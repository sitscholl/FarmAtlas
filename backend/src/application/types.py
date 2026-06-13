from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar

from ..results import FarmAtlasError, FarmAtlasWarning


ApplicationStatus = Literal["success", "warning", "skipped", "failed"]
ResultT = TypeVar("ResultT")


@dataclass(slots=True, kw_only=True)
class ApplicationFieldResult(Generic[ResultT]):
    operation_name: str
    field_id: int
    field_name: str | None = None
    result: ResultT | None = None
    warnings: list[FarmAtlasWarning] = field(default_factory=list)
    errors: list[FarmAtlasError] = field(default_factory=list)
    status: ApplicationStatus | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.warnings = _normalize_messages(self.warnings, FarmAtlasWarning)
        self.errors = _normalize_messages(self.errors, FarmAtlasError)
        if self.status is None:
            self.status = self._infer_status()

    @property
    def ok(self) -> bool:
        return self.status != "failed"

    def _infer_status(self) -> ApplicationStatus:
        if self.errors:
            return "failed"
        if self.result is None:
            return "skipped"
        if self.warnings:
            return "warning"
        return "success"


def _normalize_messages(
    value: Any,
    message_type: type[FarmAtlasWarning] | type[FarmAtlasError],
) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, message_type):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return list(value)
    raise TypeError(f"Expected {message_type.__name__} or a list of them, got {type(value).__name__}")
