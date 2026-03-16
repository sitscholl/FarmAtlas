from datetime import date

from pydantic import BaseModel


class FieldSummaryResponse(BaseModel):
    id: int
    name: str
    reference_provider: str
    reference_station: str
    soil_type: str
    humus_pct: float
    area_ha: float
    root_depth_cm: float
    p_allowable: float


class FieldOverviewResponse(BaseModel):
    id: int
    name: str
    reference_provider: str
    reference_station: str
    soil_type: str
    humus_pct: float
    area_ha: float
    root_depth_cm: float
    p_allowable: float
    water_balance_as_of: date | None
    current_deficit: float | None
    current_soil_storage: float | None
    field_capacity: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


class WaterBalanceSummaryResponse(BaseModel):
    field_id: int
    as_of: date | None
    current_deficit: float | None
    current_soil_storage: float | None
    field_capacity: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


class WaterBalanceSeriesPointResponse(BaseModel):
    date: date
    precipitation: float
    irrigation: float
    evapotranspiration: float
    incoming: float
    net: float
    soil_storage: float
    field_capacity: float
    deficit: float
    readily_available_water: float | None
    safe_ratio: float | None
    below_raw: bool | None
