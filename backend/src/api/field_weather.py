import logging
from datetime import date

from fastapi import APIRouter

from ..schemas import FieldWeatherDailyRead, FieldWeatherRefreshResponse
from .utils import raise_write_http_error, runtime, validate_field_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fields/{field_id}/weather/daily", tags=["field-weather"])


@router.get("", response_model=list[FieldWeatherDailyRead])
async def list_field_weather_daily(
    field_id: int,
    start: date | None = None,
    end: date | None = None,
):
    validate_field_id(field_id)
    with runtime.db.session_scope() as session:
        records = runtime.db.field_weather.list_for_field(session, field_id=field_id, start=start, end=end)
    return [FieldWeatherDailyRead.model_validate(record) for record in records]


@router.post("/refresh", response_model=FieldWeatherRefreshResponse)
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
