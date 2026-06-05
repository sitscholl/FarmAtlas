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
