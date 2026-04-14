from datetime import date

from pydantic import BaseModel

from .base import ORMModel


class FieldBase(BaseModel):
    group: str
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
    soil_type: str | None = None
    soil_weight: str | None = None
    humus_pct: float | None = None
    area_ha: float
    effective_root_depth_cm: float | None = None
    p_allowable: float | None = None
    drip_distance: float | None = None
    drip_discharge: float | None = None
    tree_strip_width: float | None = None
    

class FieldCreate(FieldBase):
    pass


class FieldUpdate(FieldBase):
    pass


class FieldReplant(FieldBase):
    valid_from: date


class FieldRead(FieldBase, ORMModel):
    id: int
    valid_from: date
    valid_to: date | None = None


class FieldReadGroupedSection(BaseModel):
    section: str | None = None
    field: FieldRead


class FieldReadGroupedVariety(BaseModel):
    variety: str
    field_ids: list[int]
    sections: list[FieldReadGroupedSection]


class FieldReadGroupedField(BaseModel):
    name: str
    active: bool
    field_ids: list[int]
    varieties: list[FieldReadGroupedVariety]


class FieldReadGrouped(BaseModel):
    fields: list[FieldReadGroupedField]

class FieldWaterBalanceSummary(BaseModel):
    water_balance_as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


class FieldOverview(FieldRead, FieldWaterBalanceSummary):
    pass
