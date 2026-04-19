from datetime import date

from pydantic import BaseModel, model_validator

from ..database import models
from .base import ORMModel
from .section import SectionRead


class PlantingCreate(BaseModel):
    field_id: int
    variety: str
    valid_from: date
    valid_to: date | None = None


class PlantingUpdate(BaseModel):
    variety: str
    valid_from: date
    valid_to: date | None = None


class PlantingRead(ORMModel):
    id: int
    field_id: int
    variety: str
    valid_from: date
    valid_to: date | None = None
    active: bool

    @model_validator(mode="before")
    @classmethod
    def from_orm_planting(cls, value):
        if isinstance(value, models.Planting):
            return {
                "id": value.id,
                "field_id": value.field_id,
                "variety": value.variety.name,
                "valid_from": value.valid_from,
                "valid_to": value.valid_to,
                "active": value.active,
            }
        return value


class PlantingDetailRead(PlantingRead):
    sections: list[SectionRead]

    @model_validator(mode="before")
    @classmethod
    def from_orm_planting_detail(cls, value):
        if isinstance(value, models.Planting):
            return {
                "id": value.id,
                "field_id": value.field_id,
                "variety": value.variety.name,
                "valid_from": value.valid_from,
                "valid_to": value.valid_to,
                "active": value.active,
                "sections": value.sections,
            }
        return value
