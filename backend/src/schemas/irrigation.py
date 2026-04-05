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


class IrrigationCommandCreate(BaseModel):
    field: str
    date: date | None = None
    method: str
    amount: float = 100


class IrrigationTarget(BaseModel):
    field: str
    active: bool
    field_ids: list[int]
    field_count: int
    sections: list[str] = []
    varieties: list[str] = []


class IrrigationCommandResult(BaseModel):
    status: str
    message: str
    field: str
    date: date
    method: str
    amount: float
    matched_field_ids: list[int]

    created_event_ids: list[int]
    updated_event_ids: list[int]
    unchanged_event_ids: list[int]

    created_count: int
    updated_count: int
    unchanged_count: int