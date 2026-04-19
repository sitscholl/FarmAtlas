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
    IrrigationRead,
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
