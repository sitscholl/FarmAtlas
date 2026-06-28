from datetime import date

from pydantic import BaseModel, Field

from .workflow import WorkflowFieldResponseBase


class WaterBalanceSummary(BaseModel):
    field_id: int
    as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


class WaterBalanceFieldSummaryRead(BaseModel):
    field_id: int
    field_name: str
    field_group: str
    active: bool
    effective_root_depth_cm: float | None
    last_irrigation_date: date | None
    summary: WaterBalanceSummary


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
    precipitation_missing: bool | None = None
    evapotranspiration_missing: bool | None = None


class WaterBalanceSeriesResponse(WorkflowFieldResponseBase):
    data: list[WaterBalanceSeriesPoint] = Field(default_factory=list)
