import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models

logger = logging.getLogger(__name__)


class FieldRepository:
    UPDATE_ALLOWLIST = {
        "group",
        "name",
        "reference_provider",
        "reference_station",
        "elevation",
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
        "drip_distance",
        "drip_discharge",
        "tree_strip_width",
        "valve_open",
    }

    def _query(self, session: Session):
        return session.query(models.Field).options(
            selectinload(models.Field.plantings).selectinload(models.Planting.variety),
            selectinload(models.Field.plantings).selectinload(models.Planting.sections),
            selectinload(models.Field.cadastral_parcels),
        )

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip()
        return text or None

    def _normalize_required_text(self, value: Any, *, field_name: str) -> str:
        text = str(value).strip()
        if text == "":
            raise ValueError(f"Expected a non-empty value for '{field_name}'")
        return text

    def _normalize_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "ja"}:
                return True
            if normalized in {"false", "0", "no", "n", "nein"}:
                return False
        return bool(value)

    def get_by_id(self, session: Session, field_id: int) -> models.Field | None:
        return self._query(session).filter(models.Field.id == field_id).one_or_none()

    def list_all(self, session: Session) -> list[models.Field]:
        return self._query(session).order_by(models.Field.group, models.Field.name).all()

    def create(
        self,
        session: Session,
        *,
        group: str,
        name: str,
        reference_provider: str,
        reference_station: str,
        elevation: float,
        soil_type: str | None = None,
        soil_weight: str | None = None,
        humus_pct: float | None = None,
        effective_root_depth_cm: float | None = None,
        p_allowable: float | None = None,
        drip_distance: float | None = None,
        drip_discharge: float | None = None,
        tree_strip_width: float | None = None,
        valve_open: bool = True,
    ) -> models.Field:
        field = models.Field(
            group=self._normalize_required_text(group, field_name="group"),
            name=self._normalize_required_text(name, field_name="name"),
            reference_provider=self._normalize_required_text(reference_provider, field_name="reference_provider"),
            reference_station=self._normalize_required_text(reference_station, field_name="reference_station"),
            elevation=float(elevation),
            soil_type=self._normalize_optional_text(soil_type),
            soil_weight=self._normalize_optional_text(soil_weight),
            humus_pct=None if humus_pct is None else float(humus_pct),
            effective_root_depth_cm=None if effective_root_depth_cm is None else float(effective_root_depth_cm),
            p_allowable=None if p_allowable is None else float(p_allowable),
            drip_distance=None if drip_distance is None else float(drip_distance),
            drip_discharge=None if drip_discharge is None else float(drip_discharge),
            tree_strip_width=None if tree_strip_width is None else float(tree_strip_width),
            valve_open=self._normalize_bool(valve_open),
        )
        session.add(field)
        session.flush()
        logger.debug("Added new field %s", field)
        return self.get_by_id(session, field.id) or field

    def update(self, session: Session, field_id: int, updates: dict[str, Any]) -> tuple[models.Field, set[str]]:
        field = self.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"Could not find any field with id {field_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key in {"group", "name", "reference_provider", "reference_station"}:
                new_value = self._normalize_required_text(raw_value, field_name=field_key)
            elif field_key in {"soil_type", "soil_weight"}:
                new_value = self._normalize_optional_text(raw_value)
            elif field_key == "valve_open":
                new_value = self._normalize_bool(raw_value)
            else:
                new_value = None if raw_value is None else float(raw_value)

            if getattr(field, field_key) != new_value:
                setattr(field, field_key, new_value)
                changed_keys.add(field_key)

        if not changed_keys:
            return field, changed_keys

        session.flush()
        return self.get_by_id(session, field_id) or field, changed_keys

    def delete(self, session: Session, field_id: int) -> bool:
        field = self.get_by_id(session, field_id)
        if field is None:
            return False
        session.delete(field)
        return True
