from pydantic import BaseModel

from .base import ORMModel


class VarietyBase(BaseModel):
    name: str
    group: str
    nr_per_kg: float | None = None
    kg_per_box: float | None = None
    slope: float | None = None
    intercept: float | None = None
    specific_weight: float | None = None


class VarietyCreate(VarietyBase):
    pass


class VarietyUpdate(VarietyBase):
    pass


class VarietyRead(VarietyBase, ORMModel):
    id: int
