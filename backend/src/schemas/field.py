from pydantic import BaseModel, model_validator

from ..database import models
from .base import ORMModel
from .planting import PlantingDetailRead
from .water_balance import WaterBalanceSummary


class CadastralParcelRead(ORMModel):
    id: int
    field_id: int
    parcel_id: str
    municipality_id: str
    area: float


class FieldCreate(BaseModel):
    group: str
    name: str
    reference_provider: str
    reference_station: str
    elevation: float
    soil_type: str | None = None
    soil_weight: str | None = None
    humus_pct: float | None = None
    effective_root_depth_cm: float | None = None
    p_allowable: float | None = None
    drip_distance: float | None = None
    drip_discharge: float | None = None
    tree_strip_width: float | None = None
    valve_open: bool = True


class FieldUpdate(BaseModel):
    group: str
    name: str
    reference_provider: str
    reference_station: str
    elevation: float
    soil_type: str | None = None
    soil_weight: str | None = None
    humus_pct: float | None = None
    effective_root_depth_cm: float | None = None
    p_allowable: float | None = None
    drip_distance: float | None = None
    drip_discharge: float | None = None
    tree_strip_width: float | None = None
    valve_open: bool = True


class FieldRead(ORMModel):
    id: int
    group: str
    name: str
    reference_provider: str
    reference_station: str
    elevation: float
    soil_type: str | None = None
    soil_weight: str | None = None
    humus_pct: float | None = None
    effective_root_depth_cm: float | None = None
    p_allowable: float | None = None
    drip_distance: float | None = None
    drip_discharge: float | None = None
    tree_strip_width: float | None = None
    valve_open: bool


class FieldSummaryRead(FieldRead):
    total_area: float
    tree_count: int | None = None
    running_metre: float | None = None
    active: bool
    herbicide_free: bool | None = None
    planting_count: int
    section_count: int
    variety_names: list[str]
    section_names: list[str]
    planting_year_min: int | None = None
    planting_year_max: int | None = None
    last_irrigation_date: str | None = None
    water_balance_summary: WaterBalanceSummary


class FieldDetailRead(BaseModel):
    field: FieldRead
    cadastral_parcels: list[CadastralParcelRead]
    plantings: list[PlantingDetailRead]

    @model_validator(mode="before")
    @classmethod
    def from_orm_field(cls, value):
        if isinstance(value, models.Field):
            return {
                "field": value,
                "cadastral_parcels": value.cadastral_parcels,
                "plantings": value.plantings,
            }
        return value
