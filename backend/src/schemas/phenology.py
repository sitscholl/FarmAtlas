from datetime import date

from pydantic import BaseModel, Field, model_validator

from ..database import models
from ..domain.phenology import get_phenological_stage
from .base import ORMModel


class PhenologyEventBase(BaseModel):
    section_id: int
    stage_code: str
    date: date


class PhenologyEventCreate(PhenologyEventBase):
    pass


class PhenologyBulkCreate(BaseModel):
    section_ids: list[int] = Field(min_length=1)
    stage_code: str
    date: date


class PhenologyBulkResponse(BaseModel):
    created_event_ids: list[int]
    created_count: int
    skipped_section_ids: list[int]
    errors_by_section_id: dict[int, str] = Field(default_factory=dict)


class PhenologyEventUpdate(PhenologyEventBase):
    pass


class PhenologyEventRead(ORMModel):
    id: int
    section_id: int
    stage_code: str
    date: date
    stage_name: str
    bbch_code: int | None = None
    principal_stage: int | None = None
    kc_anchor: str | None = None

    @model_validator(mode="before")
    @classmethod
    def from_orm_event(cls, value):
        if isinstance(value, models.SectionPhenologyEvent):
            stage = get_phenological_stage(value.stage_code)
            return {
                "id": value.id,
                "section_id": value.section_id,
                "stage_code": value.stage_code,
                "date": value.date,
                "stage_name": value.stage_code if stage is None else stage.label,
                "bbch_code": None if stage is None else stage.bbch_code,
                "principal_stage": None if stage is None else stage.principal_stage,
                "kc_anchor": None if stage is None else stage.kc_anchor,
            }
        return value
