from datetime import date as DateType

from pydantic import BaseModel, Field, field_validator

from .base import ORMModel


class IrrigationBase(BaseModel):
    date: DateType
    method: str
    duration: float
    amount: float | None = None

    @field_validator("method")
    @classmethod
    def _normalize_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("method must not be empty")
        return normalized

    @field_validator("duration")
    @classmethod
    def _validate_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("duration must be greater than 0")
        return value

    @field_validator("amount")
    @classmethod
    def _validate_amount(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("amount must be greater than 0")
        return value


class IrrigationCreate(IrrigationBase):
    pass


class IrrigationUpdate(IrrigationBase):
    field_id: int


class IrrigationRead(IrrigationBase, ORMModel):
    id: int
    field_id: int
    duration: float
    amount: float


class IrrigationBulkCreate(IrrigationCreate):
    field_ids: list[int]

    @field_validator("field_ids")
    @classmethod
    def _validate_field_ids(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("field_ids must contain at least one field id")
        if any(field_id <= 0 for field_id in value):
            raise ValueError("field_ids must only contain positive integers")
        return value


class IrrigationBulkResponse(BaseModel):
    created_event_ids: list[int]
    created_count: int
    skipped_field_ids: list[int]
    errors_by_field_id: dict[int, str] = Field(default_factory=dict)


class IrrigationBulkUpsertResponse(BaseModel):
    created_event_ids: list[int]
    updated_event_ids: list[int]
    unchanged_event_ids: list[int]
    created_count: int
    updated_count: int
    unchanged_count: int
    skipped_field_ids: list[int]
    errors_by_field_id: dict[int, str] = Field(default_factory=dict)
