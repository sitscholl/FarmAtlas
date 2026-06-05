from datetime import date as DateType

from pydantic import BaseModel

from .base import ORMModel


class FieldWeatherDailyRead(ORMModel):
    date: DateType
    field_id: int
    precipitation: float
    tmin: float | None = None
    tmax: float | None = None
    tmean: float | None = None
    source_provider: str
    source_station: str
    value_type: str


class FieldWeatherRefreshResponse(BaseModel):
    field_id: int
    start: DateType
    end: DateType
    upserted_count: int


class FieldWeatherBulkRefreshResponse(BaseModel):
    start: DateType
    end: DateType
    refreshed: list[FieldWeatherRefreshResponse]
    failed_field_ids: list[int]
    errors_by_field_id: dict[int, str]
    total_upserted_count: int
