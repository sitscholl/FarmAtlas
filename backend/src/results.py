from dataclasses import dataclass

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