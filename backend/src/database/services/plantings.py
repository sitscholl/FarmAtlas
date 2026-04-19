from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import PlantingRepository


class PlantingService:
    def __init__(
        self,
        core: DatabaseCore,
        plantings: PlantingRepository,
    ) -> None:
        self._core = core
        self._plantings = plantings

    def create(self, **kwargs) -> models.Planting:
        with self._core.session_scope() as session:
            return self._plantings.create(session, **kwargs)

    def update(self, planting_id: int, updates: dict[str, Any]) -> models.Planting:
        with self._core.session_scope() as session:
            updated_planting, _ = self._plantings.update(session, planting_id, updates)
            return updated_planting

    def delete(self, planting_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._plantings.delete(session, planting_id)
