import logging

from fastapi import APIRouter, Query

from ..schemas import FieldStatisticsResponse
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/production", tags=["production"])


@router.get("/field-statistics", response_model=FieldStatisticsResponse)
async def get_field_statistics(
    season_year: int | None = None,
    field_ids: list[int] | None = Query(default=None),
):
    try:
        return runtime.production_summary_service.get_field_statistics(
            season_year=season_year,
            field_ids=field_ids,
        )
    except Exception as exc:
        logger.exception("Building field statistics failed: %s", exc)
        raise_write_http_error(exc)
