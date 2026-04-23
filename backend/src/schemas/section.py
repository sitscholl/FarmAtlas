from datetime import date

from pydantic import BaseModel, Field, model_validator

from ..database import models

from .base import ORMModel
from .phenology import PhenologyEventRead


class SectionCreate(BaseModel):
    planting_id: int
    name: str
    planting_year: int
    area: float
    tree_count: int | None = None
    tree_height: float | None = None
    row_distance: float | None = None
    tree_distance: float | None = None
    running_metre: float | None = None
    herbicide_free: bool | None = None
    valid_from: date
    valid_to: date | None = None


class SectionUpdate(BaseModel):
    name: str
    planting_year: int
    area: float
    tree_count: int | None = None
    tree_height: float | None = None
    row_distance: float | None = None
    tree_distance: float | None = None
    running_metre: float | None = None
    herbicide_free: bool | None = None
    valid_from: date
    valid_to: date | None = None


class SectionRead(ORMModel):
    id: int
    planting_id: int
    name: str
    planting_year: int
    area: float
    tree_count: int | None = None
    tree_height: float | None = None
    row_distance: float | None = None
    tree_distance: float | None = None
    running_metre: float | None = None
    herbicide_free: bool | None = None
    valid_from: date
    valid_to: date | None = None
    active: bool
    current_phenology: str | None = None
    phenology_events: list[PhenologyEventRead] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def from_orm_section(cls, value):
        if isinstance(value, models.Section):
            return {
                "id": value.id,
                "planting_id": value.planting_id,
                "name": value.name,
                "planting_year": value.planting_year,
                "area": value.area,
                "tree_count": value.tree_count,
                "tree_height": value.tree_height,
                "row_distance": value.row_distance,
                "tree_distance": value.tree_distance,
                "running_metre": value.running_metre,
                "herbicide_free": value.herbicide_free,
                "valid_from": value.valid_from,
                "valid_to": value.valid_to,
                "active": value.active,
                "current_phenology": value.current_phenology,
                "phenology_events": value.phenology_events,
            }
        return value
