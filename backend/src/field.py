from dataclasses import dataclass

import pandas as pd
from datetime import date

from .database.models import Field, PhenologyEvents
from .water_content import SoilWaterEstimate


def _unique_non_null(values: list[object]) -> list[object]:
    unique: list[object] = []
    for value in values:
        if value is None or value in unique:
            continue
        unique.append(value)
    return unique


def _single_or_none(values: list[object]) -> object | None:
    unique = _unique_non_null(values)
    if len(unique) == 1:
        return unique[0]
    return None


def _sum_optional_float(values: list[float | None]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    return sum(numeric_values) if numeric_values else None


def _sum_optional_int(values: list[int | None]) -> int | None:
    numeric_values = [int(value) for value in values if value is not None]
    return sum(numeric_values) if numeric_values else None


@dataclass(frozen=True)
class PlantingContext:
    id: int
    variety: str
    valid_from: object
    valid_to: object
    active: bool


@dataclass(frozen=True)
class SectionContext:
    id: int
    name: str
    planting_id: int
    variety: str
    planting_year: int
    area: float
    tree_count: int | None
    tree_height: float | None
    row_distance: float | None
    tree_distance: float | None
    running_metre: float | None
    herbicide_free: bool | None
    valid_from: object
    valid_to: object
    active: bool
    phenology: list[PhenologyEvents]

    @property
    def current_phenology(self) -> str | None:
        phen_stages = [stage for stage in self.phenology if stage.date <= date.today()]
        return None if len(phen_stages) == 0  else phen_stages[0].stage


@dataclass
class FieldContext:
    id: int
    group: str
    name: str
    reference_provider: str
    reference_station: str
    elevation: float
    soil_type: str | None
    soil_weight: str | None
    humus_pct: float | None
    effective_root_depth_cm: float | None
    p_allowable: float | None
    drip_distance: float | None
    drip_discharge: float | None
    tree_strip_width: float | None
    valve_open: bool
    plantings: list[PlantingContext]
    sections: list[SectionContext]
    soil_water_estimate: SoilWaterEstimate | None = None
    water_balance: pd.DataFrame | None = None

    @classmethod
    def from_model(cls, field_model: Field) -> "FieldContext":
        plantings = [
            PlantingContext(
                id=planting.id,
                variety=planting.variety.name,
                valid_from=planting.valid_from,
                valid_to=planting.valid_to,
                active=planting.active,
            )
            for planting in field_model.plantings
        ]
        sections = [
            SectionContext(
                id=section.id,
                name=section.name,
                planting_id=section.planting_id,
                variety=planting.variety.name if planting.variety is not None else "",
                planting_year=section.planting_year,
                area=float(section.area),
                tree_count=section.tree_count,
                tree_height=None if section.tree_height is None else float(section.tree_height),
                row_distance=None if section.row_distance is None else float(section.row_distance),
                tree_distance=None if section.tree_distance is None else float(section.tree_distance),
                running_metre=None if section.running_metre is None else float(section.running_metre),
                herbicide_free=section.herbicide_free,
                valid_from=section.valid_from,
                valid_to=section.valid_to,
                active=section.active,
            )
            for planting in field_model.plantings
            for section in planting.sections
        ]

        return cls(
            id=field_model.id,
            group=field_model.group,
            name=field_model.name,
            reference_provider=field_model.reference_provider,
            reference_station=field_model.reference_station,
            elevation=float(field_model.elevation),
            soil_type=field_model.soil_type,
            soil_weight=field_model.soil_weight,
            humus_pct=None if field_model.humus_pct is None else float(field_model.humus_pct),
            effective_root_depth_cm=None
            if field_model.effective_root_depth_cm is None
            else float(field_model.effective_root_depth_cm),
            p_allowable=None if field_model.p_allowable is None else float(field_model.p_allowable),
            drip_distance=None if field_model.drip_distance is None else float(field_model.drip_distance),
            drip_discharge=None if field_model.drip_discharge is None else float(field_model.drip_discharge),
            tree_strip_width=None if field_model.tree_strip_width is None else float(field_model.tree_strip_width),
            valve_open=bool(field_model.valve_open),
            plantings=plantings,
            sections=sections,
        )

    @property
    def active(self) -> bool:
        return any(section.active for section in self.sections) or any(planting.active for planting in self.plantings)

    @property
    def variety(self) -> str | None:
        values = [section.variety for section in self.sections if section.variety != ""]
        if values:
            result = _single_or_none(values)
            return None if result is None else str(result)

        planting_values = [planting.variety for planting in self.plantings]
        result = _single_or_none(planting_values)
        return None if result is None else str(result)

    @property
    def section(self) -> str | None:
        result = _single_or_none([section.name for section in self.sections])
        return None if result is None else str(result)

    @property
    def planting_year(self) -> int | None:
        result = _single_or_none([section.planting_year for section in self.sections])
        return None if result is None else int(result)

    @property
    def tree_count(self) -> int | None:
        return _sum_optional_int([section.tree_count for section in self.sections])

    @property
    def tree_height(self) -> float | None:
        result = _single_or_none([section.tree_height for section in self.sections])
        return None if result is None else float(result)

    @property
    def row_distance(self) -> float | None:
        result = _single_or_none([section.row_distance for section in self.sections])
        return None if result is None else float(result)

    @property
    def tree_distance(self) -> float | None:
        result = _single_or_none([section.tree_distance for section in self.sections])
        return None if result is None else float(result)

    @property
    def running_metre(self) -> float | None:
        return _sum_optional_float([section.running_metre for section in self.sections])

    @property
    def herbicide_free(self) -> bool | None:
        result = _single_or_none([section.herbicide_free for section in self.sections])
        return None if result is None else bool(result)

    @property
    def area(self) -> float:
        return sum(section.area for section in self.sections)

    @property
    def valid_from(self):
        dates = [section.valid_from for section in self.sections]
        if not dates:
            dates = [planting.valid_from for planting in self.plantings]
        return min(dates) if dates else None

    @property
    def valid_to(self):
        dates = [section.valid_to for section in self.sections if section.valid_to is not None]
        if not dates:
            dates = [planting.valid_to for planting in self.plantings if planting.valid_to is not None]
        return max(dates) if dates else None

    @property
    def phenology(self):
        all_stages = [i.current_phenology for i in self.sections]
        return _single_or_none(all_stages)