from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import NutrientRequirementRepository


class NutrientRequirementService:
    def __init__(
        self,
        core: DatabaseCore,
        nutrients: NutrientRequirementRepository,
    ) -> None:
        self._core = core
        self._nutrients = nutrients

    def create(self, **kwargs) -> models.NutrientRequirement:
        with self._core.session_scope() as session:
            return self._nutrients.create(session, **kwargs)

    def update(self, nutrient_id: int, updates: dict[str, Any]) -> models.NutrientRequirement:
        with self._core.session_scope() as session:
            updated_nutrient, _ = self._nutrients.update(session, nutrient_id, updates)
            return updated_nutrient

    def delete(self, nutrient_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._nutrients.delete(session, nutrient_id)