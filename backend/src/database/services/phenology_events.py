from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import PhenologyEventRepository


class PhenologyEventService:
    def __init__(
        self,
        core: DatabaseCore,
        events: PhenologyEventRepository,
    ) -> None:
        self._core = core
        self._events = events

    def create(self, **kwargs) -> models.SectionPhenologyEvent:
        with self._core.session_scope() as session:
            return self._events.create(session, **kwargs)

    def update(self, event_id: int, updates: dict[str, Any]) -> models.SectionPhenologyEvent:
        with self._core.session_scope() as session:
            updated_event, _ = self._events.update(session, event_id, updates)
            return updated_event

    def delete(self, event_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._events.delete(session, event_id)
