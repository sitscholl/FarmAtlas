import logging
from datetime import date

from fastapi import APIRouter

from ..schemas import FieldWeatherBulkRefreshResponse, FieldWeatherDailyRead, FieldWeatherRefreshResponse
from .utils import get_write_error_detail, raise_write_http_error, runtime, validate_field_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["field-weather"])


@router.get("/api/fields/{field_id}/weather/daily", response_model=list[FieldWeatherDailyRead])
async def list_field_weather_daily(
    field_id: int,
    start: date | None = None,
    end: date | None = None,
):
    validate_field_id(field_id)
    with runtime.db.session_scope() as session:
        records = runtime.db.field_weather.list_for_field(session, field_id=field_id, start=start, end=end)
    return [FieldWeatherDailyRead.model_validate(record) for record in records]


@router.post("/api/fields/{field_id}/weather/daily/refresh", response_model=FieldWeatherRefreshResponse)
async def refresh_field_weather_daily(
    field_id: int,
    start: date,
    end: date,
):
    field = validate_field_id(field_id)
    try:
        upserted_count = runtime.field_weather_service.refresh_field(field, start=start, end=end)
        return FieldWeatherRefreshResponse(
            field_id=field_id,
            start=start,
            end=end,
            upserted_count=upserted_count,
        )
    except Exception as exc:
        logger.exception("Refreshing field weather for field %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id",))


@router.post("/api/weather/daily/refresh", response_model=FieldWeatherBulkRefreshResponse)
async def refresh_all_field_weather_daily(
    start: date,
    end: date,
):
    refreshed: list[FieldWeatherRefreshResponse] = []
    failed_field_ids: list[int] = []
    errors_by_field_id: dict[int, str] = {}

    for field in runtime.fields:
        try:
            upserted_count = runtime.field_weather_service.refresh_field(field, start=start, end=end)
            refreshed.append(
                FieldWeatherRefreshResponse(
                    field_id=field.id,
                    start=start,
                    end=end,
                    upserted_count=upserted_count,
                )
            )
        except Exception as exc:
            logger.exception("Refreshing field weather for field %s failed: %s", field.id, exc)
            failed_field_ids.append(field.id)
            errors_by_field_id[field.id] = get_write_error_detail(exc)

    return FieldWeatherBulkRefreshResponse(
        start=start,
        end=end,
        refreshed=refreshed,
        failed_field_ids=failed_field_ids,
        errors_by_field_id=errors_by_field_id,
        total_upserted_count=sum(item.upserted_count for item in refreshed),
    )
