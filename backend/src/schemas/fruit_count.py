from datetime import date as Date, datetime

from pydantic import BaseModel, Field, model_validator

from .base import ORMModel


class FruitCountSampleCreate(BaseModel):
    tree_label: str | None = None
    apple_count: int
    notes: str | None = None


class FruitCountSampleUpdate(BaseModel):
    tree_label: str | None = None
    apple_count: int | None = None
    notes: str | None = None


class FruitCountSampleRead(ORMModel):
    id: int
    survey_id: int
    tree_label: str | None = None
    apple_count: int
    notes: str | None = None


class FruitCountSurveyCreate(BaseModel):
    season_year: int
    date: Date
    timing_code: str
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    method: str | None = None
    observer: str | None = None
    notes: str | None = None
    include_in_aggregation: bool = True
    quality_flag: str | None = None
    samples: list[FruitCountSampleCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope(self):
        if sum(value is not None for value in (self.field_id, self.planting_id, self.section_id)) != 1:
            raise ValueError("Exactly one of field_id, planting_id, or section_id is required")
        return self


class FruitCountSurveyDraftCreate(BaseModel):
    season_year: int
    date: Date
    timing_code: str
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    method: str | None = None
    observer: str | None = None
    notes: str | None = None
    include_in_aggregation: bool = True
    quality_flag: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if sum(value is not None for value in (self.field_id, self.planting_id, self.section_id)) != 1:
            raise ValueError("Exactly one of field_id, planting_id, or section_id is required")
        return self


class FruitCountSurveyUpdate(BaseModel):
    season_year: int | None = None
    date: Date | None = None
    timing_code: str | None = None
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    method: str | None = None
    observer: str | None = None
    notes: str | None = None
    include_in_aggregation: bool | None = None
    quality_flag: str | None = None
    samples: list[FruitCountSampleCreate] | None = None


class FruitCountSurveyRead(ORMModel):
    id: int
    season_year: int
    date: Date
    timing_code: str
    field_id: int | None = None
    planting_id: int | None = None
    section_id: int | None = None
    method: str | None = None
    observer: str | None = None
    notes: str | None = None
    include_in_aggregation: bool
    quality_flag: str | None = None
    created_at: datetime
    samples: list[FruitCountSampleRead] = Field(default_factory=list)
