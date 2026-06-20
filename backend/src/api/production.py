import logging

from fastapi import APIRouter, Query

from ..schemas import PlantingYearComparisonResponse
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/production", tags=["production"])


@router.get("/planting-year-comparison", response_model=PlantingYearComparisonResponse)
async def get_planting_year_comparison(
    season_year: int,
    history_years: int = Query(default=5, ge=2),
    field_ids: list[int] | None = Query(default=None),
):
    try:
        return runtime.production_summary_service.get_planting_year_comparison(
            season_year=season_year,
            history_years=history_years,
            field_ids=field_ids,
        )
    except Exception as exc:
        logger.exception("Building planting year comparison failed: %s", exc)
        raise_write_http_error(exc)
