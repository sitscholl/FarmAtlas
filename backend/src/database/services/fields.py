from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import FieldRepository, WaterBalanceRepository
class FieldService:
    def __init__(
        self,
        core: DatabaseCore,
        fields: FieldRepository,
        water_balance: WaterBalanceRepository,
        *,
        water_balance_trigger_fields: set[str],
    ) -> None:
        self._core = core
        self._fields = fields
        self._water_balance = water_balance
        self._water_balance_trigger_fields = water_balance_trigger_fields

    def update(self, field_id: int, updates: dict[str, Any]) -> models.Field:
        with self._core.session_scope() as session:
            updated_field, changed_keys = self._fields.update(session, field_id, updates)
            if changed_keys & self._water_balance_trigger_fields:
                self._water_balance.clear_for_field(session, updated_field.id)
            return updated_field
