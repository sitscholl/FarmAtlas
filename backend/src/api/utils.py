from contextlib import asynccontextmanager
from datetime import datetime
import logging
from pathlib import Path
import re

import pandas as pd
from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError

from ..app_config import get_app_config_path
from ..application.types import ApplicationFieldResult
from ..runtime import RuntimeContext
from ..scheduler import WorkflowScheduler
from ..schemas import (
    FieldDetailRead,
    FieldRead,
    FieldSummaryRead,
    IrrigationRead,
    NutrientRequirementRead,
    PhenologyEventRead,
    PlantingRead,
    SectionRead,
    VarietyRead,
    WaterBalanceSeriesPoint,
    WaterBalanceSeriesResponse,
    WaterBalanceSummary,
    WorkflowErrorRead,
    WorkflowWarningRead,
)
from ..domain.field import FieldContext

logger = logging.getLogger(__name__)

runtime = RuntimeContext.from_config_file(get_app_config_path())
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
    active_sections = field_context.active_sections
    active_planting_ids = {planting.id for planting in field_context.active_plantings}
    active_planting_ids.update(section.planting_id for section in active_sections)
    active_variety_names = {section.variety for section in active_sections if section.variety}
    if not active_variety_names:
        active_variety_names = {planting.variety for planting in field_context.active_plantings}
    planting_years = [section.planting_year for section in active_sections]
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
        current_phenology=field_context.current_phenology,
        herbicide_free=field_context.herbicide_free,
        planting_count=len(active_planting_ids),
        section_count=len(active_sections),
        variety_names=sorted(active_variety_names),
        section_names=sorted({section.name for section in active_sections}),
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


def serialize_nutrient_requirement(nutrient_requirement) -> NutrientRequirementRead:
    return NutrientRequirementRead.model_validate(nutrient_requirement)


def serialize_phenology_event(event) -> PhenologyEventRead:
    return PhenologyEventRead.model_validate(event)


_INTEGRITY_ERROR_MESSAGES = {
    "fields.group, fields.name": "A field with this group and name already exists.",
    "varieties.name": "A variety with this name already exists.",
    "plantings.field_id, plantings.variety_id, plantings.valid_from": (
        "A planting with this variety and start date already exists for this field."
    ),
    "sections.planting_id, sections.name": "A section with this name already exists in this planting.",
    "field_cadastral_parcels.field_id, field_cadastral_parcels.municipality_id, field_cadastral_parcels.parcel_id": (
        "This cadastral parcel is already assigned to the field."
    ),
    "nutrients.nutrient_code": "A default nutrient requirement for this nutrient code already exists.",
    "nutrients.nutrient_code, nutrients.variety_id": (
        "A nutrient requirement for this nutrient code and variety already exists."
    ),
    "irrigation_events.field_id, irrigation_events.date": "An irrigation event for this field and date already exists.",
    "section_phenology_events.section_id, section_phenology_events.date": (
        "A phenology event for this section and date already exists."
    ),
    "section_phenology_events.section_id, section_phenology_events.stage_code, section_phenology_events.year": (
        "This phenology stage is already recorded for this section and year."
    ),
    "ck_plantings_valid_range": "valid_to must be greater than or equal to valid_from",
    "ck_sections_valid_range": "valid_to must be greater than or equal to valid_from",
    "ck_field_cadastral_parcels_area_non_negative": "area must be greater than or equal to 0",
    "ck_fruit_count_surveys_one_scope": "Exactly one of field_id, planting_id, or section_id is required.",
    "ck_fruit_count_surveys_season_year": "season_year must be greater than or equal to 1900.",
    "ck_fruit_count_samples_apple_count_non_negative": "apple_count must be greater than or equal to 0.",
    "ck_yearly_stats_one_scope": "Exactly one of field_id, planting_id, or section_id is required.",
    "ck_yearly_stats_season_year": "season_year must be greater than or equal to 1900.",
    "ck_yearly_stats_thinning_hours": "thinning_hours must be greater than or equal to 0.",
    "ck_yearly_stats_harvest_hours": "harvest_hours must be greater than or equal to 0.",
    "ck_yearly_stats_filled_boxes": "filled_boxes must be greater than or equal to 0.",
    "ck_yearly_stats_yield_kg": "yield_kg must be greater than or equal to 0.",
}


def get_write_error_detail(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, IntegrityError):
        raw_detail = str(exc.orig).strip() if getattr(exc, "orig", None) is not None else str(exc).strip()

        unique_match = re.search(r"UNIQUE constraint failed: (?P<columns>.+)", raw_detail)
        if unique_match:
            columns = unique_match.group("columns").strip()
            return _INTEGRITY_ERROR_MESSAGES.get(columns, f"Unique constraint violated for {columns}.")

        check_match = re.search(r"CHECK constraint failed: (?P<constraint>.+)", raw_detail)
        if check_match:
            constraint = check_match.group("constraint").strip()
            return _INTEGRITY_ERROR_MESSAGES.get(constraint, f"Check constraint failed: {constraint}.")

        if "FOREIGN KEY constraint failed" in raw_detail:
            return "The request references related data that does not exist or cannot be deleted."

        if raw_detail:
            return raw_detail

        return "Resource already exists or violates a database constraint."
    if isinstance(exc, ValueError):
        return str(exc)
    return "Unexpected server error."


def raise_write_http_error(exc: Exception, *, not_found_prefixes: tuple[str, ...] = ()) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    detail = get_write_error_detail(exc)
    if isinstance(exc, IntegrityError):
        raise HTTPException(status_code=409, detail=detail) from exc
    if isinstance(exc, ValueError):
        status_code = 404 if any(detail.startswith(prefix) for prefix in not_found_prefixes) else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise HTTPException(status_code=500, detail=detail) from exc


def get_irrigation_event(event_id: int):
    with runtime.db.session_scope() as session:
        event = runtime.db.irrigation.get_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find any irrigation event with id {event_id}",
        )
    return event


def serialize_forecast_water_balance(dataframe: pd.DataFrame) -> list[WaterBalanceSeriesPoint]:
    series = dataframe.reset_index()
    if "date" not in series.columns:
        index_column = dataframe.index.name or "index"
        if index_column in series.columns:
            series = series.rename(columns={index_column: "date"})
        else:
            series = series.rename(columns={series.columns[0]: "date"})
    return [
        WaterBalanceSeriesPoint(
            date=pd.Timestamp(row["date"]).date(),
            precipitation=float(row["precipitation"]),
            irrigation=float(row["irrigation"]),
            evapotranspiration=float(row["evapotranspiration"]),
            kc=None if pd.isna(row.get("kc")) else float(row["kc"]),
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
            precipitation_missing=None
            if pd.isna(row.get("precipitation_missing"))
            else bool(row["precipitation_missing"]),
            evapotranspiration_missing=None
            if pd.isna(row.get("evapotranspiration_missing"))
            else bool(row["evapotranspiration_missing"]),
        )
        for _, row in series.iterrows()
    ]


def serialize_result_messages(
    result,
) -> tuple[list[WorkflowWarningRead], list[WorkflowErrorRead]]:
    warnings = [
        WorkflowWarningRead(
            message=warning.message,
            code=warning.code,
            details=warning.details,
        )
        for warning in result.warnings
    ]
    errors = [
        WorkflowErrorRead(
            message=error.message,
            code=error.code,
            exception_type=error.exception_type,
            details=error.details,
            fatal=error.fatal,
        )
        for error in result.errors
    ]
    return warnings, errors


def serialize_water_balance_summary(summary) -> WaterBalanceSummary:
    return WaterBalanceSummary(
        field_id=summary.field_id,
        as_of=summary.as_of,
        current_water_deficit=summary.current_water_deficit,
        current_soil_water_content=summary.current_soil_water_content,
        available_water_storage=summary.available_water_storage,
        readily_available_water=summary.readily_available_water,
        below_raw=summary.below_raw,
        safe_ratio=summary.safe_ratio,
    )


def serialize_water_balance_application_result(
    result: ApplicationFieldResult[pd.DataFrame],
) -> WaterBalanceSeriesResponse:
    warnings, errors = serialize_result_messages(result)
    dataframe = result.result
    data = [] if dataframe is None or dataframe.empty else serialize_forecast_water_balance(dataframe)
    return WaterBalanceSeriesResponse(
        workflow_name=result.operation_name,
        field_id=result.field_id,
        field_name=result.field_name,
        status=result.status or "skipped",
        ok=result.ok,
        warnings=warnings,
        errors=errors,
        metadata=result.metadata,
        data=data,
    )
