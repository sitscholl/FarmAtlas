from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import IrrigationRepository, WaterBalanceRepository


class IrrigationService:
    def __init__(
        self,
        core: DatabaseCore,
        irrigation: IrrigationRepository,
        water_balance: WaterBalanceRepository,
    ) -> None:
        self._core = core
        self._irrigation = irrigation
        self._water_balance = water_balance

    def create(
        self,
        *,
        field_id: int,
        date,
        method: str,
        amount: float,
    ) -> models.Irrigation:
        with self._core.session_scope() as session:
            event = self._irrigation.create(
                session,
                field_id=field_id,
                date=date,
                method=method,
                amount=amount,
            )
            self._water_balance.clear_for_field(session, field_id)
            return event

    def update(self, event_id: int, updates: dict[str, Any]) -> models.Irrigation:
        with self._core.session_scope() as session:
            existing_event = self._irrigation.get_by_id(session, event_id)
            if existing_event is None:
                raise ValueError(f"Could not find any irrigation event with id {event_id}")

            old_field_id = existing_event.field_id
            updated_event = self._irrigation.update(session, event_id, updates)
            self._water_balance.clear_for_field(session, updated_event.field_id)
            if old_field_id != updated_event.field_id:
                self._water_balance.clear_for_field(session, old_field_id)
            return updated_event

    def delete(self, event_id: int) -> tuple[bool, int | None]:
        with self._core.session_scope() as session:
            existing_event = self._irrigation.get_by_id(session, event_id)
            if existing_event is None:
                return False, None

            deleted = self._irrigation.delete(session, event_id)
            if deleted:
                self._water_balance.clear_for_field(session, existing_event.field_id)
            return deleted, existing_event.field_id

    def clear_for_field(self, field_id: int) -> int:
        with self._core.session_scope() as session:
            deleted = self._irrigation.clear_for_field(session, field_id)
            self._water_balance.clear_for_field(session, field_id)
            return deleted
