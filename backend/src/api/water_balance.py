import logging

from fastapi import APIRouter, Query, status

from ..schemas import WaterBalanceSeriesResponse, WaterBalanceSummary
from .utils import (
    raise_write_http_error,
    runtime,
    serialize_water_balance_workflow_result,
    validate_field_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["water-balance"])


@router.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummary])
async def get_water_balance_summary():
    return runtime.water_balance_service.get_summaries(runtime.fields)


@router.get("/api/fields/{field_id}/water-balance/summary", response_model=WaterBalanceSummary)
async def get_field_water_balance_summary(field_id: int):
    field_context = validate_field_id(field_id)
    return runtime.water_balance_service.get_summary_for_field(field_context)


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
    return serialize_water_balance_workflow_result(calculation_result)


@router.post("/api/fields/{field_id}/water-balance", response_model=WaterBalanceSummary, status_code=status.HTTP_200_OK)
async def trigger_water_balance_calculation(field_id: int):
    field_context = validate_field_id(field_id)
    try:
        return runtime.water_balance_service.get_summary_for_field(field_context)
    except Exception as exc:
        logger.exception("Calculating water balance for field with id %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Unknown field id", "No field with id"))
