from datetime import datetime

from pydantic import BaseModel, model_validator

from .base import ORMModel


class YearlyStatsCreate(BaseModel):
    season_year: int
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    thinning_hours: float | None = None
    harvest_hours: float | None = None
    filled_boxes: float | None = None
    yield_kg: float | None = None
    revenue: float | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if sum(value is not None for value in (self.field_id, self.planting_id, self.section_id)) != 1:
            raise ValueError("Exactly one of field_id, planting_id, or section_id is required")
        return self


class YearlyStatsUpdate(BaseModel):
    season_year: int | None = None
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    thinning_hours: float | None = None
    harvest_hours: float | None = None
    filled_boxes: float | None = None
    yield_kg: float | None = None
    revenue: float | None = None
    notes: str | None = None


class YearlyStatsRead(ORMModel):
    id: int
    season_year: int
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    thinning_hours: float | None = None
    harvest_hours: float | None = None
    filled_boxes: float | None = None
    yield_kg: float | None = None
    revenue: float | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
