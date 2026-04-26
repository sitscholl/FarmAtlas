from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import PhenologyEventRepository, WaterBalanceRepository


class PhenologyEventService:
    def __init__(
        self,
        core: DatabaseCore,
        events: PhenologyEventRepository,
        water_balance: WaterBalanceRepository,
    ) -> None:
        self._core = core
        self._events = events
        self._water_balance = water_balance

    def _field_id_for_event(self, event: models.SectionPhenologyEvent) -> int | None:
        section = event.section
        if section is None or section.planting is None:
            return None
        return section.planting.field_id

    def create(self, **kwargs) -> models.SectionPhenologyEvent:
        with self._core.session_scope() as session:
            event = self._events.create(session, **kwargs)
            field_id = self._field_id_for_event(event)
            if field_id is not None:
                self._water_balance.clear_for_field(session, field_id)
            return event

    def update(self, event_id: int, updates: dict[str, Any]) -> models.SectionPhenologyEvent:
        with self._core.session_scope() as session:
            existing = self._events.get_by_id(session, event_id)
            old_field_id = None if existing is None else self._field_id_for_event(existing)
            updated_event, changed_keys = self._events.update(session, event_id, updates)
            new_field_id = self._field_id_for_event(updated_event)
            if changed_keys:
                for field_id in {old_field_id, new_field_id}:
                    if field_id is not None:
                        self._water_balance.clear_for_field(session, field_id)
            return updated_event

    def delete(self, event_id: int) -> bool:
        with self._core.session_scope() as session:
            existing = self._events.get_by_id(session, event_id)
            field_id = None if existing is None else self._field_id_for_event(existing)
            deleted = self._events.delete(session, event_id)
            if deleted and field_id is not None:
                self._water_balance.clear_for_field(session, field_id)
            return deleted
