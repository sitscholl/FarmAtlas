from dataclasses import dataclass, field
from typing import Any
import traceback as traceback_module


@dataclass(slots=True)
class FarmAtlasWarning:
    message: str
    code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FarmAtlasError:
    message: str
    code: str | None = None
    exception_type: str | None = None
    traceback: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
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
    ) -> "FarmAtlasError":
        return cls(
            message=message or str(exc) or exc.__class__.__name__,
            code=code,
            exception_type=exc.__class__.__name__,
            traceback="".join(traceback_module.format_exception(exc)) if include_traceback else None,
            details=details or {},
        )
