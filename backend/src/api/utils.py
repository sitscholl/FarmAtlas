from contextlib import asynccontextmanager
from datetime import datetime
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
    FieldSummaryRead,
    IrrigationRead,
    PlantingRead,
    SectionRead,
    VarietyRead,
    WaterBalanceSeriesPoint,
    WaterBalanceSummary,
)
from ..field import FieldContext

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


def serialize_field_summary(
    field,
    *,
    water_balance_summary: WaterBalanceSummary,
    last_irrigation_date,
) -> FieldSummaryRead:
    field_context = FieldContext.from_model(field)
    planting_years = [section.planting_year for section in field_context.sections]
    return FieldSummaryRead(
        id=field.id,
        group=field.group,
        name=field.name,
        reference_provider=field.reference_provider,
        reference_station=field.reference_station,
        elevation=float(field.elevation),
        soil_type=field.soil_type,
        soil_weight=field.soil_weight,
        humus_pct=None if field.humus_pct is None else float(field.humus_pct),
        effective_root_depth_cm=None if field.effective_root_depth_cm is None else float(field.effective_root_depth_cm),
        p_allowable=None if field.p_allowable is None else float(field.p_allowable),
        drip_distance=None if field.drip_distance is None else float(field.drip_distance),
        drip_discharge=None if field.drip_discharge is None else float(field.drip_discharge),
        tree_strip_width=None if field.tree_strip_width is None else float(field.tree_strip_width),
        valve_open=bool(field.valve_open),
        total_area=float(field_context.area),
        tree_count=field_context.tree_count,
        running_metre=field_context.running_metre,
        active=field_context.active,
        herbicide_free=field_context.herbicide_free,
        planting_count=len(field.plantings),
        section_count=len(field_context.sections),
        variety_names=sorted({planting.variety for planting in field_context.plantings}),
        section_names=sorted({section.name for section in field_context.sections}),
        planting_year_min=min(planting_years) if planting_years else None,
        planting_year_max=max(planting_years) if planting_years else None,
        last_irrigation_date=None if last_irrigation_date is None else last_irrigation_date.isoformat(),
        water_balance_summary=water_balance_summary,
    )


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


def get_irrigation_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.irrigation.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    return event


def queue_water_balance_refresh(background_tasks: BackgroundTasks, field_ids: list[int]) -> None:
    for field_id in sorted(set(field_ids)):
        background_tasks.add_task(runtime.run_workflow_for_field, "water_balance", field_id)


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
