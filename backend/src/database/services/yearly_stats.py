from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import YearlyStatsRepository


class YearlyStatsService:
    def __init__(
        self,
        core: DatabaseCore,
        yearly_stats: YearlyStatsRepository,
    ) -> None:
        self._core = core
        self._yearly_stats = yearly_stats

    def create(self, **kwargs) -> models.YearlyStats:
        with self._core.session_scope() as session:
            return self._yearly_stats.create(session, **kwargs)

    def update(self, stats_id: int, updates: dict[str, Any]) -> models.YearlyStats:
        with self._core.session_scope() as session:
            return self._yearly_stats.update(session, stats_id, updates)

    def delete(self, stats_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._yearly_stats.delete(session, stats_id)
