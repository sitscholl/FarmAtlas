import logging

from fastapi import APIRouter, HTTPException, status

from ..schemas import YearlyStatsCreate, YearlyStatsRead, YearlyStatsUpdate
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/yearly-stats", tags=["yearly-stats"])


@router.get("", response_model=list[YearlyStatsRead])
async def list_yearly_stats(
    season_year: int | None = None,
    field_id: int | None = None,
    planting_id: int | None = None,
    section_id: int | None = None,
):
    with runtime.db.session_scope() as session:
        stats = runtime.db.yearly_stats.list_stats(
            session,
            season_year=season_year,
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
        )
    return [YearlyStatsRead.model_validate(item) for item in stats]


@router.get("/{stats_id}", response_model=YearlyStatsRead)
async def get_yearly_stats(stats_id: int):
    with runtime.db.session_scope() as session:
        stats = runtime.db.yearly_stats.get_by_id(session, stats_id)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Could not find any yearly stats with id {stats_id}")
    return YearlyStatsRead.model_validate(stats)


@router.post("", response_model=YearlyStatsRead, status_code=status.HTTP_201_CREATED)
async def create_yearly_stats(stats: YearlyStatsCreate):
    try:
        new_stats = runtime.db.yearly_stats_service.create(**stats.model_dump())
        return YearlyStatsRead.model_validate(new_stats)
    except Exception as exc:
        logger.exception("Adding yearly stats failed: %s", exc)
        raise_write_http_error(exc)


@router.put("/{stats_id}", response_model=YearlyStatsRead)
async def update_yearly_stats(stats_id: int, stats: YearlyStatsUpdate):
    try:
        updated_stats = runtime.db.yearly_stats_service.update(
            stats_id=stats_id,
            updates=stats.model_dump(exclude_unset=True),
        )
        return YearlyStatsRead.model_validate(updated_stats)
    except Exception as exc:
        logger.exception("Updating yearly stats %s failed: %s", stats_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any yearly stats with id",))


@router.delete("/{stats_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_yearly_stats(stats_id: int):
    deleted = runtime.db.yearly_stats_service.delete(stats_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any yearly stats with id {stats_id}")
