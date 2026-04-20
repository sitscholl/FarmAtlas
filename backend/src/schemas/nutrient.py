from pydantic import BaseModel, model_validator

from ..database import models
from .base import ORMModel


class NutrientRequirementBase(BaseModel):
    variety: str | None = None
    nutrient_code: str
    requirement_per_kg_min: float
    requirement_per_kg_mean: float
    requirement_per_kg_max: float

    @model_validator(mode="after")
    def validate_requirement_range(self):
        if self.requirement_per_kg_min <= 0:
            raise ValueError("requirement_per_kg_min must be greater than 0")
        if self.requirement_per_kg_mean <= 0:
            raise ValueError("requirement_per_kg_mean must be greater than 0")
        if self.requirement_per_kg_max <= 0:
            raise ValueError("requirement_per_kg_max must be greater than 0")
        if self.requirement_per_kg_min > self.requirement_per_kg_mean:
            raise ValueError("requirement_per_kg_min must be less than or equal to requirement_per_kg_mean")
        if self.requirement_per_kg_mean > self.requirement_per_kg_max:
            raise ValueError("requirement_per_kg_mean must be less than or equal to requirement_per_kg_max")
        return self


class NutrientRequirementCreate(NutrientRequirementBase):
    pass


class NutrientRequirementUpdate(NutrientRequirementBase):
    pass


class NutrientRequirementRead(ORMModel):
    id: int
    variety: str | None = None
    nutrient_code: str
    requirement_per_kg_min: float
    requirement_per_kg_mean: float
    requirement_per_kg_max: float

    @model_validator(mode="before")
    @classmethod
    def from_orm_nutrient_requirement(cls, value):
        if isinstance(value, models.NutrientRequirement):
            return {
                "id": value.id,
                "variety": None if value.variety is None else value.variety.name,
                "nutrient_code": value.nutrient_code,
                "requirement_per_kg_min": value.requirement_per_kg_min,
                "requirement_per_kg_mean": value.requirement_per_kg_mean,
                "requirement_per_kg_max": value.requirement_per_kg_max,
            }
        return value
