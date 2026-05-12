from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..field import FieldContext

@dataclass
class WorkflowError:
    message: str
    traceback: str

@dataclass
class WorkflowWarning:
    message: str

@dataclass
class WorkflowFieldResult:
    workflow_name: str
    field_id: int
    result: Any | None = None
    warnings: WorkflowWarning | None = None
    errors: WorkflowError | None = None

class BaseWorkflow(ABC):

    @abstractmethod
    def run_field(self, field: FieldContext, **kwargs) -> WorkflowFieldResult:
        pass
    @abstractmethod
    def run(self, fields: list[FieldContext], **kwargs) -> list[WorkflowFieldResult]:
        pass