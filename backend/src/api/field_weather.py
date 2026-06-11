import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter

from ..schemas import FieldWeatherBulkRefreshResponse, FieldWeatherRefreshResponse, StationWeatherHourlyRead
from .utils import get_write_error_detail, raise_write_http_error, runtime, validate_field_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["field-weather"])


def _optional_float(value) -> float | None:
    return None if pd.isna(value) else float(value)


@router.get("/api/fields/{field_id}/weather/hourly", response_model=list[StationWeatherHourlyRead])
async def list_field_weather_hourly(
    field_id: int,
    start: datetime,
    end: datetime,
    ensure: bool = True,
):
    field = validate_field_id(field_id)
    try:
        if ensure:
            weather = runtime.field_weather_service.get_field_hourly_weather(field, start=start, end=end, ensure=True)
            return [
                StationWeatherHourlyRead(
                    source_provider=str(row["source_provider"]),
                    source_station=str(row["source_station"]),
                    timestamp=timestamp.to_pydatetime(),
                    precipitation=float(row["precipitation"]),
                    tair_2m=_optional_float(row["tair_2m"]),
                    relative_humidity=_optional_float(row["relative_humidity"]),
                    wind_speed=_optional_float(row["wind_speed"]),
                    wind_gust=_optional_float(row["wind_gust"]),
                    air_pressure=_optional_float(row["air_pressure"]),
                    sun_duration=_optional_float(row["sun_duration"]),
                    solar_radiation=_optional_float(row["solar_radiation"]),
                    et0=_optional_float(row["et0"]),
                    et0_corrected=_optional_float(row["et0_corrected"]),
                    value_type=str(row["value_type"]),
                    updated_at=row["updated_at"].to_pydatetime(),
                )
                for timestamp, row in weather.data.iterrows()
            ]

        with runtime.db.session_scope() as session:
            records = runtime.db.field_weather.list_station_hourly(
                session,
                provider=field.reference_provider,
                station=field.reference_station,
                start=start,
                end=end,
            )
        return [StationWeatherHourlyRead.model_validate(record) for record in records]
    except Exception as exc:
        logger.exception("Listing hourly weather for field %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id",))


@router.post("/api/fields/{field_id}/weather/hourly/refresh", response_model=FieldWeatherRefreshResponse)
async def refresh_field_weather_hourly(
    field_id: int,
    start: datetime,
    end: datetime,
):
    field = validate_field_id(field_id)
    try:
        result = runtime.field_weather_service.refresh_station_hourly(
            provider=field.reference_provider,
            station=field.reference_station,
            start=start,
            end=end,
        )
        return FieldWeatherRefreshResponse(
            field_id=field_id,
            source_provider=result.source_provider,
            source_station=result.source_station,
            start=result.start.to_pydatetime(),
            end=result.end.to_pydatetime(),
            upserted_count=result.upserted_count,
        )
    except Exception as exc:
        logger.exception("Refreshing hourly weather for field %s failed: %s", field_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("No field with id",))


@router.post("/api/weather/hourly/refresh", response_model=FieldWeatherBulkRefreshResponse)
async def refresh_all_field_weather_hourly(
    start: datetime,
    end: datetime,
):
    refreshed: list[FieldWeatherRefreshResponse] = []
    failed_field_ids: list[int] = []
    errors_by_field_id: dict[int, str] = {}

    for field in runtime.fields:
        try:
            result = runtime.field_weather_service.refresh_station_hourly(
                provider=field.reference_provider,
                station=field.reference_station,
                start=start,
                end=end,
            )
            refreshed.append(
                FieldWeatherRefreshResponse(
                    field_id=field.id,
                    source_provider=result.source_provider,
                    source_station=result.source_station,
                    start=result.start.to_pydatetime(),
                    end=result.end.to_pydatetime(),
                    upserted_count=result.upserted_count,
                )
            )
        except Exception as exc:
            logger.exception("Refreshing hourly weather for field %s failed: %s", field.id, exc)
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
