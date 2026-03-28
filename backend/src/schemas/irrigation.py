from datetime import date

from pydantic import BaseModel

from .base import ORMModel


class IrrigationBase(BaseModel):
    date: date
    method: str
    amount: float = 100


class IrrigationCreate(IrrigationBase):
    pass


class IrrigationUpdate(IrrigationBase):
    field_id: int


class IrrigationRead(IrrigationBase, ORMModel):
    id: int
    field_id: int
    amount: float
