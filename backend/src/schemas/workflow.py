from typing import Any

from pydantic import BaseModel, Field


class WorkflowWarningRead(BaseModel):
    message: str
    code: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowErrorRead(BaseModel):
    message: str
    code: str | None = None
    exception_type: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    fatal: bool = True


class WorkflowFieldResponseBase(BaseModel):
    workflow_name: str
    field_id: int
    field_name: str | None = None
    status: str
    ok: bool
    warnings: list[WorkflowWarningRead] = Field(default_factory=list)
    errors: list[WorkflowErrorRead] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
