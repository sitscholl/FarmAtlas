from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import PhenologicalStageRepository


class PhenologicalStageService:
    def __init__(
        self,
        core: DatabaseCore,
        stages: PhenologicalStageRepository,
    ) -> None:
        self._core = core
        self._stages = stages

    def create(self, **kwargs) -> models.PhenologicalStage:
        with self._core.session_scope() as session:
            return self._stages.create(session, **kwargs)

    def update(self, stage_id: int, updates: dict[str, Any]) -> models.PhenologicalStage:
        with self._core.session_scope() as session:
            updated_stage, _ = self._stages.update(session, stage_id, updates)
            return updated_stage

    def delete(self, stage_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._stages.delete(session, stage_id)
