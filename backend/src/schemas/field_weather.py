from datetime import datetime as DateTimeType
from typing import Any

from pydantic import BaseModel, Field

from .base import ORMModel


class StationWeatherHourlyRead(ORMModel):
    source_provider: str
    source_station: str
    timestamp: DateTimeType
    precipitation: float
    tair_2m: float | None = None
    relative_humidity: float | None = None
    wind_speed: float | None = None
    wind_gust: float | None = None
    air_pressure: float | None = None
    sun_duration: float | None = None
    solar_radiation: float | None = None
    et0: float | None = None
    value_type: str
    updated_at: DateTimeType


class FieldWeatherRefreshResponse(BaseModel):
    field_id: int
    source_provider: str
    source_station: str
    start: DateTimeType
    end: DateTimeType
    upserted_count: int


class FieldWeatherBulkRefreshResponse(BaseModel):
    start: DateTimeType
    end: DateTimeType
    refreshed: list[FieldWeatherRefreshResponse]
    failed_field_ids: list[int]
    errors_by_field_id: dict[int, str]
    total_upserted_count: int


class WeatherCacheRefreshStationResult(BaseModel):
    workflow_name: str
    source_provider: str
    source_station: str
    cache_kind: str
    status: str
    start: DateTimeType
    end: DateTimeType
    field_ids: list[int]
    row_count: int = 0
    refreshed: bool = False
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WeatherCacheRefreshResponse(BaseModel):
    status: str
    message: str
    workflow_name: str
    station_count: int
    field_count: int
    start: DateTimeType
    end: DateTimeType
    cleaned_row_count: int = 0
    results: list[WeatherCacheRefreshStationResult]
