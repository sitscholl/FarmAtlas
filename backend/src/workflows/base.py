from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field as dataclass_field
import traceback as traceback_module
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, TypeVar

if TYPE_CHECKING:
    from ..field import FieldContext


WorkflowStatus = Literal["success", "warning", "skipped", "failed"]
ResultT = TypeVar("ResultT")


@dataclass(slots=True)
class WorkflowError:
    message: str
    code: str | None = None
    exception_type: str | None = None
    traceback: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)
    fatal: bool = True

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        *,
        message: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        include_traceback: bool = True,
    ) -> "WorkflowError":
        return cls(
            message=message or str(exc) or exc.__class__.__name__,
            code=code,
            exception_type=exc.__class__.__name__,
            traceback="".join(traceback_module.format_exception(exc)) if include_traceback else None,
            details=details or {},
        )


@dataclass(slots=True)
class WorkflowWarning:
    message: str
    code: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class WorkflowFieldResult(Generic[ResultT]):
    workflow_name: str
    field_id: int
    field_name: str | None = None
    result: ResultT | None = None
    warnings: list[WorkflowWarning] = dataclass_field(default_factory=list)
    errors: list[WorkflowError] = dataclass_field(default_factory=list)
    status: WorkflowStatus | None = None
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)

    def __post_init__(self) -> None:
        self.warnings = _normalize_messages(self.warnings, WorkflowWarning)
        self.errors = _normalize_messages(self.errors, WorkflowError)
        if self.status is None:
            self.status = self._infer_status()

    @property
    def ok(self) -> bool:
        return self.status != "failed"

    def _infer_status(self) -> WorkflowStatus:
        if self.errors:
            return "failed"
        if self.result is None:
            return "skipped"
        if self.warnings:
            return "warning"
        return "success"


def _normalize_messages(
    value: Any,
    message_type: type[WorkflowWarning] | type[WorkflowError],
) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, message_type):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return list(value)
    raise TypeError(f"Expected {message_type.__name__} or a list of them, got {type(value).__name__}")


class BaseWorkflow(ABC):
    workflow_name: ClassVar[str | None] = None
    result_class: ClassVar[type[WorkflowFieldResult[Any]]] = WorkflowFieldResult

    @property
    def name(self) -> str:
        return self.workflow_name or self.__class__.__name__

    def field_result(
        self,
        field: FieldContext,
        *,
        result: Any | None = None,
        warnings: WorkflowWarning | Iterable[WorkflowWarning] | None = None,
        errors: WorkflowError | Iterable[WorkflowError] | None = None,
        status: WorkflowStatus | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowFieldResult[Any]:
        return self.result_class(
            workflow_name=self.name,
            field_id=field.id,
            field_name=field.name,
            result=result,
            warnings=warnings,
            errors=errors,
            status=status,
            metadata=metadata or {},
        )

    def field_error_result(
        self,
        field: FieldContext,
        exc: Exception,
        *,
        message: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> WorkflowFieldResult[Any]:
        return self.field_result(
            field,
            errors=WorkflowError.from_exception(
                exc,
                message=message,
                code=code,
                details=details,
            ),
        )

    @abstractmethod
    def run_field(self, field: FieldContext, **kwargs) -> WorkflowFieldResult:
        pass

    @abstractmethod
    def run(self, fields: list[FieldContext], **kwargs) -> list[WorkflowFieldResult]:
        pass
