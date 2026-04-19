from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
import logging
from pathlib import Path

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..runtime import RuntimeContext
from ..scheduler import WorkflowScheduler
from ..schemas import (
    FieldDetailRead,
    FieldRead,
    IrrigationCommandCreate,
    IrrigationCommandResult,
    IrrigationRead,
    IrrigationTarget,
    PlantingRead,
    SectionRead,
    VarietyRead,
    WaterBalanceSeriesPoint,
    WaterBalanceSummary,
)

logger = logging.getLogger(__name__)

runtime = RuntimeContext.from_config_file("config/config.yaml")
scheduler = WorkflowScheduler(runtime=runtime)

frontend_dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
frontend_assets_dir = frontend_dist_dir / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = runtime
    app.state.scheduler = scheduler
    scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


def validate_field_id(field_id: int):
    try:
        return runtime.get_field(field_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def serialize_field(field) -> FieldRead:
    return FieldRead.model_validate(field)


def serialize_field_detail(field) -> FieldDetailRead:
    return FieldDetailRead.model_validate(field)


def serialize_planting(planting) -> PlantingRead:
    return PlantingRead.model_validate(planting)


def serialize_section(section) -> SectionRead:
    return SectionRead.model_validate(section)


def serialize_irrigation_event(event) -> IrrigationRead:
    return IrrigationRead.model_validate(event)


def serialize_variety(variety) -> VarietyRead:
    return VarietyRead.model_validate(variety)


def raise_write_http_error(exc: Exception, *, not_found_prefixes: tuple[str, ...] = ()) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, IntegrityError):
        raise HTTPException(status_code=409, detail="Resource already exists or violates a uniqueness constraint.") from exc
    if isinstance(exc, ValueError):
        detail = str(exc)
        status_code = 404 if any(detail.startswith(prefix) for prefix in not_found_prefixes) else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise HTTPException(status_code=500, detail="Unexpected server error.") from exc


def today_local() -> date:
    return datetime.now(runtime.timezone).date()


def get_irrigation_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.irrigation.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    return event


def get_fields_by_name(field_name: str, *, active_only: bool = True):
    normalized = field_name.strip().casefold()
    matches = [
        field
        for field in runtime.fields
        if field.name.strip().casefold() == normalized and (field.active or not active_only)
    ]
    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any {'active ' if active_only else ''}field with name '{field_name}'",
        )
    return matches


def get_irrigation_events_for_fields_and_date(field_ids: list[int], target_date: date) -> dict[int, object]:
    if not field_ids:
        return {}

    field_id_set = set(field_ids)
    with runtime.db.session_scope() as session:
        events = [
            event
            for event in runtime.db.irrigation.list(
                session,
                start=target_date,
                end=target_date + timedelta(days=1),
            )
            if event.field_id in field_id_set and event.date == target_date
        ]
    return {event.field_id: event for event in events}


def queue_water_balance_refresh(background_tasks: BackgroundTasks, field_ids: list[int]) -> None:
    for field_id in sorted(set(field_ids)):
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)


def build_irrigation_targets() -> list[IrrigationTarget]:
    grouped: dict[str, list] = {}

    for field in runtime.fields:
        grouped.setdefault(field.name, []).append(field)

    targets: list[IrrigationTarget] = []
    for field_name, fields in grouped.items():
        active_fields = [field for field in fields if field.active]
        target_fields = active_fields if active_fields else fields

        sections = sorted(
            {
                field.section
                for field in target_fields
                if field.section is not None and field.section != ""
            }
        )
        varieties = sorted(
            {
                field.variety
                for field in target_fields
                if getattr(field, "variety", None) is not None
            }
        )

        targets.append(
            IrrigationTarget(
                field=field_name,
                active=any(field.active for field in fields),
                field_ids=[field.id for field in target_fields],
                field_count=len(target_fields),
                sections=sections,
                varieties=varieties,
            )
        )

    return sorted(targets, key=lambda target: target.field.casefold())


def build_irrigation_command_result(
    *,
    success: bool,
    status_value: str,
    message: str,
    irrigation_command: IrrigationCommandCreate,
    target_date: date,
    matched_field_ids: list[int] | None = None,
    created_event_ids: list[int] | None = None,
    updated_event_ids: list[int] | None = None,
    unchanged_event_ids: list[int] | None = None,
    error: str | None = None,
) -> IrrigationCommandResult:
    created_event_ids = created_event_ids or []
    updated_event_ids = updated_event_ids or []
    unchanged_event_ids = unchanged_event_ids or []
    matched_field_ids = matched_field_ids or []

    return IrrigationCommandResult(
        success=success,
        status=status_value,
        message=message,
        field=irrigation_command.field,
        date=target_date,
        method=irrigation_command.method,
        duration=irrigation_command.duration,
        amount=irrigation_command.amount,
        matched_field_ids=matched_field_ids,
        error=error,
        created_event_ids=created_event_ids,
        updated_event_ids=updated_event_ids,
        unchanged_event_ids=unchanged_event_ids,
        created_count=len(created_event_ids),
        updated_count=len(updated_event_ids),
        unchanged_count=len(unchanged_event_ids),
    )


def serialize_water_balance_series(records) -> list[WaterBalanceSeriesPoint]:
    return [
        WaterBalanceSeriesPoint(
            date=record.date,
            precipitation=record.precipitation,
            irrigation=record.irrigation,
            evapotranspiration=record.evapotranspiration,
            incoming=record.incoming,
            net=record.net,
            soil_water_content=record.soil_water_content,
            available_water_storage=record.available_water_storage,
            water_deficit=record.water_deficit,
            readily_available_water=record.readily_available_water,
            safe_ratio=record.safe_ratio,
            below_raw=None if record.below_raw is None else bool(record.below_raw),
            value_type="observed",
            model="observation",
        )
        for record in records
    ]


def serialize_forecast_water_balance(dataframe: pd.DataFrame) -> list[WaterBalanceSeriesPoint]:
    series = dataframe.reset_index().rename(columns={"index": "date"})
    return [
        WaterBalanceSeriesPoint(
            date=pd.Timestamp(row["date"]).date(),
            precipitation=float(row["precipitation"]),
            irrigation=float(row["irrigation"]),
            evapotranspiration=float(row["evapotranspiration"]),
            incoming=float(row["incoming"]),
            net=float(row["net"]),
            soil_water_content=float(row["soil_water_content"]),
            available_water_storage=float(row["available_water_storage"]),
            water_deficit=float(row["water_deficit"]),
            readily_available_water=None if pd.isna(row.get("readily_available_water")) else float(row["readily_available_water"]),
            safe_ratio=None if pd.isna(row.get("safe_ratio")) else float(row["safe_ratio"]),
            below_raw=None if pd.isna(row.get("below_raw")) else bool(row["below_raw"]),
            value_type=None if pd.isna(row.get("value_type")) else str(row["value_type"]),
            model=None if pd.isna(row.get("model")) else str(row["model"]),
        )
        for _, row in series.iterrows()
    ]


def get_water_balance_summary_for_field(field_id: int) -> WaterBalanceSummary:
    with runtime.db.session_scope() as session:
        summaries = runtime.db.water_balance.get_summary(session, field_ids=[field_id])
    if not summaries:
        return WaterBalanceSummary(
            field_id=field_id,
            as_of=None,
            current_water_deficit=None,
            current_soil_water_content=None,
            available_water_storage=None,
            readily_available_water=None,
            below_raw=None,
            safe_ratio=None,
        )
    return WaterBalanceSummary(**summaries[0])
