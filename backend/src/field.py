from dataclasses import dataclass, field

import pandas as pd

from .database.models import Field
from .field_capacity import FieldCapacity


@dataclass
class FieldResults:
    field_capacity: FieldCapacity | None = None
    water_balance: pd.DataFrame | None = None
    metrics: dict[str, object] = field(default_factory=dict)


@dataclass
class FieldContext:
    id: int
    name: str
    reference_station: str
    soil_type: str
    humus_pct: float
    area_ha: float
    root_depth_cm: float
    p_allowable: float

    @classmethod
    def from_model(cls, field_model: Field) -> "FieldContext":
        return cls(
            id=field_model.id,
            name=field_model.name,
            reference_station=field_model.reference_station,
            soil_type=field_model.soil_type,
            humus_pct=field_model.humus_pct,
            area_ha=field_model.area_ha,
            root_depth_cm=field_model.root_depth_cm,
            p_allowable=field_model.p_allowable,
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
    def soil_type(self) -> str:
        return self.field.soil_type

    @property
    def humus_pct(self) -> float:
        return self.field.humus_pct

    @property
    def area_ha(self) -> float | None:
        return self.field.area_ha

    @property
    def root_depth_cm(self) -> float:
        return self.field.root_depth_cm

    @property
    def p_allowable(self) -> float | None:
        return self.field.p_allowable

    @property
    def metrics(self) -> dict[str, object]:
        return self.results.metrics

    @property
    def field_capacity(self) -> FieldCapacity | None:
        return self.results.field_capacity

    @field_capacity.setter
    def field_capacity(self, value: FieldCapacity | None) -> None:
        self.results.field_capacity = value

    @property
    def water_balance(self) -> pd.DataFrame | None:
        return self.results.water_balance

    @water_balance.setter
    def water_balance(self, value: pd.DataFrame | None) -> None:
        self.results.water_balance = value
