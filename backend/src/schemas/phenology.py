from datetime import date

from pydantic import BaseModel, model_validator

from ..database import models
from .base import ORMModel


class PhenologyEventBase(BaseModel):
    section_id: int
    stage_id: int
    date: date


class PhenologyEventCreate(PhenologyEventBase):
    pass


class PhenologyEventUpdate(PhenologyEventBase):
    pass


class PhenologyEventRead(ORMModel):
    id: int
    section_id: int
    stage_id: int
    date: date
    stage_name: str
    kc: float

    @model_validator(mode="before")
    @classmethod
    def from_orm_event(cls, value):
        if isinstance(value, models.SectionPhenologyEvent):
            return {
                "id": value.id,
                "section_id": value.section_id,
                "stage_id": value.stage_id,
                "date": value.date,
                "stage_name": value.stage.name,
                "kc": value.stage.kc,
            }
        return value
