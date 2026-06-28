from fastapi import APIRouter, Query

from ..schemas import WaterBalanceFieldSummaryRead, WaterBalanceSeriesResponse, WaterBalanceSummary
from .utils import (
    runtime,
    serialize_water_balance_application_result,
    serialize_water_balance_field_summary,
    serialize_water_balance_summary,
    validate_field_id,
)

router = APIRouter(tags=["water-balance"])


@router.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummary])
async def get_water_balance_summary():
    return [
        serialize_water_balance_summary(summary)
        for summary in runtime.water_balance_service.get_summaries(runtime.fields)
    ]


@router.get("/api/fields/water-balance/table", response_model=list[WaterBalanceFieldSummaryRead])
async def get_water_balance_table():
    with runtime.db.session_scope() as session:
        fields = runtime.db.fields.list_all(session)
        latest_irrigation_dates = runtime.db.irrigation.get_latest_dates(
            session,
            field_ids=[field.id for field in fields],
        )

    field_contexts = runtime.get_fields_by_ids([field.id for field in fields])
    water_balance_summaries = {
        summary.field_id: serialize_water_balance_summary(summary)
        for summary in runtime.water_balance_service.get_summaries(field_contexts)
    }

    return [
        serialize_water_balance_field_summary(
            field,
            water_balance_summary=water_balance_summaries.get(field.id)
            or WaterBalanceSummary(
                field_id=field.id,
                as_of=None,
                current_water_deficit=None,
                current_soil_water_content=None,
                available_water_storage=None,
                readily_available_water=None,
                below_raw=None,
                safe_ratio=None,
            ),
            last_irrigation_date=latest_irrigation_dates.get(field.id),
        )
        for field in fields
    ]


@router.get("/api/fields/{field_id}/water-balance/summary", response_model=WaterBalanceSummary)
async def get_field_water_balance_summary(field_id: int):
    field_context = validate_field_id(field_id)
    return serialize_water_balance_summary(runtime.water_balance_service.get_summary_for_field(field_context))


@router.get("/api/fields/{field_id}/water-balance/series", response_model=WaterBalanceSeriesResponse)
async def get_field_water_balance_series(
    field_id: int,
    forecast_days: int = Query(default=0, ge=0, le=14),
):
    field_context = validate_field_id(field_id)
    calculation_result = runtime.water_balance_service.calculate_field(
        field_context,
        forecast_days=forecast_days,
    )
    return serialize_water_balance_application_result(calculation_result)

