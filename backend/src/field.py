from datetime import date
from dataclasses import dataclass, field

import pandas as pd

from .database.models import Field
from .water_content import SoilWaterEstimate


@dataclass
class FieldResults:
    soil_water_estimate: SoilWaterEstimate | None = None
    water_balance: pd.DataFrame | None = None
    metrics: dict[str, object] = field(default_factory=dict)


@dataclass
class FieldContext:
    id: int
    group: str
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
    soil_type: str | None
    soil_weight: str | None
    humus_pct: float | None
    area_ha: float
    effective_root_depth_cm: float | None
    p_allowable: float | None
    drip_distance: float | None
    drip_discharge: float | None
    tree_strip_width: float | None
    valid_from: date
    valid_to: date | None

    @classmethod
    def from_model(cls, field_model: Field) -> "FieldContext":
        return cls(
            id=field_model.id,
            group=field_model.group,
            name=field_model.name,
            section=field_model.section,
            variety=field_model.variety,
            planting_year=field_model.planting_year,
            tree_count=field_model.tree_count,
            tree_height=field_model.tree_height,
            row_distance=field_model.row_distance,
            tree_distance=field_model.tree_distance,
            running_metre=field_model.running_metre,
            herbicide_free=field_model.herbicide_free,
            active=field_model.active,
            reference_provider=field_model.reference_provider,
            reference_station=field_model.reference_station,
            soil_type=field_model.soil_type,
            soil_weight=field_model.soil_weight,
            humus_pct=field_model.humus_pct,
            area_ha=field_model.area_ha,
            effective_root_depth_cm=field_model.effective_root_depth_cm,
            p_allowable=field_model.p_allowable,
            drip_distance=field_model.drip_distance,
            drip_discharge=field_model.drip_discharge,
            tree_strip_width=field_model.tree_strip_width,
            valid_from=field_model.valid_from,
            valid_to=field_model.valid_to,
        )


@dataclass
class FieldState:
    field: FieldContext
    results: FieldResults = field(default_factory=FieldResults)

    @classmethod
    def from_context(cls, field_context: FieldContext) -> "FieldState":
        return cls(field=field_context)

    @property
    def id(self) -> int:
        return self.field.id

    @property
    def name(self) -> str:
        return self.field.name

    @property
    def reference_station(self) -> str:
        return self.field.reference_station

    @property
    def reference_provider(self) -> str:
        return self.field.reference_provider

    @property
    def soil_type(self) -> str | None:
        return self.field.soil_type

    @property
    def humus_pct(self) -> float | None:
        return self.field.humus_pct

    @property
    def area_ha(self) -> float | None:
        return self.field.area_ha

    @property
    def soil_weight(self) -> str | None:
        return self.field.soil_weight

    @property
    def effective_root_depth_cm(self) -> float | None:
        return self.field.effective_root_depth_cm

    @property
    def p_allowable(self) -> float | None:
        return self.field.p_allowable

    @property
    def metrics(self) -> dict[str, object]:
        return self.results.metrics

    @property
    def soil_water_estimate(self) -> SoilWaterEstimate | None:
        return self.results.soil_water_estimate

    @soil_water_estimate.setter
    def soil_water_estimate(self, value: SoilWaterEstimate | None) -> None:
        self.results.soil_water_estimate = value

    @property
    def water_balance(self) -> pd.DataFrame | None:
        return self.results.water_balance

    @water_balance.setter
    def water_balance(self, value: pd.DataFrame | None) -> None:
        self.results.water_balance = value
