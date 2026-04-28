from datetime import date

from pydantic import BaseModel


class WaterBalanceSummary(BaseModel):
    field_id: int
    as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


class WaterBalanceSeriesPoint(BaseModel):
    date: date
    precipitation: float
    irrigation: float
    evapotranspiration: float
    kc: float | None = None
    incoming: float
    net: float
    soil_water_content: float
    available_water_storage: float
    water_deficit: float
    readily_available_water: float | None
    safe_ratio: float | None
    below_raw: bool | None
    value_type: str | None
    model: str | None
