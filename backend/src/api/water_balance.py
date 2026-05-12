import logging

from fastapi import APIRouter, Query, status

from ..schemas import WaterBalanceSeriesResponse, WaterBalanceSummary
from .utils import (
    get_water_balance_summary_for_field,
    raise_write_http_error,
    runtime,
    serialize_water_balance_workflow_result,
    validate_field_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["water-balance"])


@router.get("/api/fields/water-balance/summary", response_model=list[WaterBalanceSummary])
async def get_water_balance_summary():
    with runtime.db.session_scope() as session:
        summaries = runtime.db.water_balance.get_summary(session)
    return [WaterBalanceSummary(**summary) for summary in summaries]


@router.get("/api/fields/{field_id}/water-balance/summary", response_model=WaterBalanceSummary)
async def get_field_water_balance_summary(field_id: int):
    validate_field_id(field_id)
    return get_water_balance_summary_for_field(field_id)


@router.get("/api/fields/{field_id}/water-balance/series", response_model=WaterBalanceSeriesResponse)
async def get_field_water_balance_series(
    field_id: int,
    forecast_days: int = Query(default=0, ge=0, le=14),
):
    field_context = validate_field_id(field_id)

    if forecast_days > 0:
        workflow_result = runtime.run_workflow_for_field(
            "water_balance",
            field_id,
            persist=True,
            forecast_days=forecast_days,
        )
        if workflow_result is None:
            workflow_result = runtime.workflows.water_balance.field_result(field_context, status="skipped")
        return serialize_water_balance_workflow_result(workflow_result)

    water_balance = runtime.workflows.water_balance.get_cached_water_balance(field_context)
    workflow_result = runtime.workflows.water_balance.field_result(
        field_context,
        result=None if water_balance is None or water_balance.empty else water_balance,
        metadata={"source": "cache"},
    )
    return serialize_water_balance_workflow_result(workflow_result)


@router.post("/api/fields/{field_id}/water-balance", response_model=WaterBalanceSummary, status_code=status.HTTP_200_OK)
async def trigger_water_balance_calculation(field_id: int):
    validate_field_id(field_id)
    try:
        with runtime.db.session_scope() as session:
            runtime.db.water_balance.clear_for_field(session, field_id)
        workflow_result = runtime.run_workflow_for_field("water_balance", field_id)
        if workflow_result is not None and not workflow_result.ok:
            error = workflow_result.errors[0] if workflow_result.errors else None
            message = error.message if error is not None else "Water balance workflow failed."
            raise RuntimeError(message)
        return get_water_balance_summary_for_field(field_id)
    except Exception as exc:
        logger.exception("Refreshing water balance for field with id %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Unknown field id", "No field with id"))
