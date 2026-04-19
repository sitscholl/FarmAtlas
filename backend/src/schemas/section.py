from datetime import date

from pydantic import BaseModel

from .base import ORMModel


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
