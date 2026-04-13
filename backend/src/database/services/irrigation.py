from typing import Any

from .. import models
from ..core import DatabaseCore
from ..repositories import FieldRepository, IrrigationRepository, WaterBalanceRepository


class IrrigationService:
    def __init__(
        self,
        core: DatabaseCore,
        fields: FieldRepository,
        irrigation: IrrigationRepository,
        water_balance: WaterBalanceRepository,
    ) -> None:
        self._core = core
        self._fields = fields
        self._irrigation = irrigation
        self._water_balance = water_balance

    def resolve_amount(
        self,
        *,
        field: models.Field,
        method: str,
        duration: float,
        amount: float | None,
    ) -> float:
        if amount is not None:
            return float(amount)

        normalized_method = method.strip().lower()
        if normalized_method != "drip":
            raise ValueError(
                f"Automatic amount calculation is only supported for drip irrigation. "
                f"Provide 'amount' manually for method '{method}'."
            )

        missing_fields = [
            field_name
            for field_name in ("drip_distance", "drip_discharge", "tree_strip_width")
            if getattr(field, field_name) in (None, 0)
        ]
        if missing_fields:
            raise ValueError(
                f"Field {field.id} is missing drip settings required for automatic amount calculation: "
                f"{', '.join(missing_fields)}"
            )

        drip_distance = float(field.drip_distance)
        drip_discharge = float(field.drip_discharge)
        tree_strip_width = float(field.tree_strip_width)
        duration = float(duration)

        if drip_distance <= 0 or drip_discharge <= 0 or tree_strip_width <= 0:
            raise ValueError(
                "drip_distance, drip_discharge, tree_strip_width, and duration must be greater than 0 "
                "for automatic amount calculation."
            )
        if duration <= 0:
            raise ValueError("duration must be greater than 0 for automatic amount calculation.")

        return duration * drip_discharge / drip_distance / tree_strip_width

    def create(
        self,
        *,
        field_id: int,
        date,
        method: str,
        duration: float,
        amount: float | None,
    ) -> models.Irrigation:
        with self._core.session_scope() as session:
            field = self._fields.get_by_id(session, field_id)
            if field is None:
                raise ValueError(f"No field with id '{field_id}' found")

            event = self._irrigation.create(
                session,
                field_id=field_id,
                date=date,
                method=method,
                duration=float(duration),
                amount=self.resolve_amount(
                    field=field,
                    method=method,
                    duration=duration,
                    amount=amount,
                ),
            )
            self._water_balance.clear_for_field(session, field_id)
            return event

    def update(self, event_id: int, updates: dict[str, Any]) -> models.Irrigation:
        with self._core.session_scope() as session:
            existing_event = self._irrigation.get_by_id(session, event_id)
            if existing_event is None:
                raise ValueError(f"Could not find any irrigation event with id {event_id}")

            old_field_id = existing_event.field_id
            field_id = int(updates.get("field_id", existing_event.field_id))
            field = self._fields.get_by_id(session, field_id)
            if field is None:
                raise ValueError(f"No field with id '{field_id}' found")

            method = str(updates.get("method", existing_event.method))
            duration = float(updates.get("duration", existing_event.duration))
            amount_supplied = updates["amount"] if "amount" in updates else existing_event.amount

            updates = {
                **updates,
                "field_id": field_id,
                "method": method,
                "duration": duration,
                "amount": self.resolve_amount(
                    field=field,
                    method=method,
                    duration=duration,
                    amount=amount_supplied,
                ),
            }
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
