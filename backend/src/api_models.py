from datetime import date

from pydantic import BaseModel


class FieldSummaryResponse(BaseModel):
    id: int
    name: str
    section: str | None
    variety: str
    planting_year: int
    tree_count: int | None
    tree_height: float | None
    row_distance: float | None
    tree_distance: float | None
    running_metre: float | None
    herbicide_free: bool | None
    active: bool
    reference_provider: str
    reference_station: str
    soil_type: str
    soil_weight: str | None
    humus_pct: float
    area_ha: float
    effective_root_depth_cm: float
    p_allowable: float

class FieldPost(BaseModel):
    name: str
    section: str | None = None
    variety: str
    planting_year: int
    tree_count: int | None = None
    tree_height: float | None = None
    row_distance: float | None = None
    tree_distance: float | None = None
    running_metre: float | None = None
    herbicide_free: bool | None = None
    active: bool = True
    reference_provider: str
    reference_station: str
    soil_type: str
    soil_weight: str | None = None
    humus_pct: float
    area_ha: float
    effective_root_depth_cm: float
    p_allowable: float

class FieldPut(BaseModel):
    name: str
    section: str | None = None
    variety: str
    planting_year: int
    tree_count: int | None = None
    tree_height: float | None = None
    row_distance: float | None = None
    tree_distance: float | None = None
    running_metre: float | None = None
    herbicide_free: bool | None = None
    active: bool = True
    reference_provider: str
    reference_station: str
    soil_type: str
    soil_weight: str | None = None
    humus_pct: float
    area_ha: float
    effective_root_depth_cm: float
    p_allowable: float

class FieldOverviewResponse(BaseModel):
    id: int
    name: str
    section: str | None
    variety: str
    planting_year: int
    tree_count: int | None
    tree_height: float | None
    row_distance: float | None
    tree_distance: float | None
    running_metre: float | None
    herbicide_free: bool | None
    active: bool
    reference_provider: str
    reference_station: str
    soil_type: str
    soil_weight: str | None
    humus_pct: float
    area_ha: float
    effective_root_depth_cm: float
    p_allowable: float
    water_balance_as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None

class IrrigationResponse(BaseModel):
    id: int
    field_id: int
    date: date
    method: str
    amount: float = 100

class IrrigationPost(BaseModel):
    date: date
    method: str
    amount: float = 100

class IrrigationPut(BaseModel):
    field_id: int
    date: date
    method: str
    amount: float = 100

class WaterBalanceSummaryResponse(BaseModel):
    field_id: int
    as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
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
    soil_water_content: float
    available_water_storage: float
    water_deficit: float
    readily_available_water: float | None
    safe_ratio: float | None
    below_raw: bool | None
    value_type: str | None = None
    model: str | None = None
