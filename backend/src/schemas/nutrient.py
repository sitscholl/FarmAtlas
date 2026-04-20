from pydantic import BaseModel, model_validator

from ..database import models
from .base import ORMModel


class NutrientRequirementBase(BaseModel):
    variety: str | None = None
    nutrient_code: str
    requirement_per_kg_yield: float


class NutrientRequirementCreate(NutrientRequirementBase):
    pass


class NutrientRequirementUpdate(NutrientRequirementBase):
    pass


class NutrientRequirementRead(ORMModel):
    id: int
    variety: str | None = None
    nutrient_code: str
    requirement_per_kg_yield: float

    @model_validator(mode="before")
    @classmethod
    def from_orm_nutrient_requirement(cls, value):
        if isinstance(value, models.NutrientRequirement):
            return {
                "id": value.id,
                "variety": None if value.variety is None else value.variety.name,
                "nutrient_code": value.nutrient_code,
                "requirement_per_kg_yield": value.requirement_per_kg_yield,
            }
        return value
