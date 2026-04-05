from datetime import date as DateType

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from .base import ORMModel


class IrrigationBase(BaseModel):
    date: DateType
    method: str
    amount: float = Field(default=100, gt=0)

    @field_validator("method")
    @classmethod
    def _normalize_method(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("method must not be empty")
        return normalized


class IrrigationCreate(IrrigationBase):
    pass


class IrrigationUpdate(IrrigationBase):
    field_id: int


class IrrigationRead(IrrigationBase, ORMModel):
    id: int
    field_id: int
    amount: float


class IrrigationCommandCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    field: str = Field(validation_alias=AliasChoices("field", "field_name"))
    date: DateType | None = None
    method: str
    amount: float = Field(default=100, gt=0)

    @field_validator("field", "method")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class IrrigationTarget(BaseModel):
    field: str
    active: bool
    field_ids: list[int]
    field_count: int
    sections: list[str] = Field(default_factory=list)
    varieties: list[str] = Field(default_factory=list)


class IrrigationCommandResult(BaseModel):
    success: bool
    status: str
    message: str
    field: str
    date: DateType
    method: str
    amount: float
    matched_field_ids: list[int]
    error: str | None = None

    created_event_ids: list[int]
    updated_event_ids: list[int]
    unchanged_event_ids: list[int]

    created_count: int
    updated_count: int
    unchanged_count: int
