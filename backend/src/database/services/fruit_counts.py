from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import FruitCountRepository


class FruitCountService:
    def __init__(
        self,
        core: DatabaseCore,
        fruit_counts: FruitCountRepository,
    ) -> None:
        self._core = core
        self._fruit_counts = fruit_counts

    def create(self, **kwargs) -> models.FruitCountSurvey:
        with self._core.session_scope() as session:
            return self._fruit_counts.create(session, **kwargs)

    def create_draft(self, **kwargs) -> models.FruitCountSurvey:
        with self._core.session_scope() as session:
            return self._fruit_counts.create_draft(session, **kwargs)

    def update(self, survey_id: int, updates: dict[str, Any]) -> models.FruitCountSurvey:
        with self._core.session_scope() as session:
            return self._fruit_counts.update(session, survey_id, updates)

    def add_sample(self, survey_id: int, sample: dict[str, Any]) -> models.FruitCountSample:
        with self._core.session_scope() as session:
            return self._fruit_counts.add_sample(session, survey_id=survey_id, sample=sample)

    def update_sample(self, sample_id: int, updates: dict[str, Any]) -> models.FruitCountSample:
        with self._core.session_scope() as session:
            return self._fruit_counts.update_sample(session, sample_id=sample_id, updates=updates)

    def delete_sample(self, sample_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._fruit_counts.delete_sample(session, sample_id)

    def delete(self, survey_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._fruit_counts.delete(session, survey_id)
