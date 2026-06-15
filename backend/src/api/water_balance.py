from fastapi import APIRouter, Query

from ..schemas import WaterBalanceSeriesResponse, WaterBalanceSummary
from .utils import (
    runtime,
    serialize_water_balance_application_result,
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

