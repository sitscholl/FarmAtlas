import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models

logger = logging.getLogger(__name__)


class FieldRepository:
    UPDATE_ALLOWLIST = {
        "group",
        "name",
        "section",
        "variety",
        "planting_year",
        "reference_provider",
        "reference_station",
        "soil_type",
        "soil_weight",
        "humus_pct",
        "area",
        "effective_root_depth_cm",
        "p_allowable",
        "drip_distance",
        "drip_discharge",
        "tree_strip_width",
        "tree_count",
        "tree_height",
        "row_distance",
        "tree_distance",
        "running_metre",
        "herbicide_free",
        "active",
    }

    def _query(self, session: Session):
        return session.query(models.Field).options(selectinload(models.Field.variety_ref))

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

    def _get_variety_by_name(self, session: Session, variety_name: str) -> models.Variety:
        variety = (
            session.query(models.Variety)
            .filter(models.Variety.name == str(variety_name).strip())
            .one_or_none()
        )
        if variety is None:
            raise ValueError(
                f"Unknown variety '{variety_name}'. Create the variety master data before assigning it to a field."
            )
        return variety

    def _apply_updates(
        self,
        session: Session,
        field: models.Field,
        updates: dict[str, Any],
    ) -> set[str]:
        changed_keys: set[str] = set()

        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key == "group":
                new_value = self._normalize_required_text(raw_value, field_name="group")
                if field.group != new_value:
                    field.group = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "name":
                new_value = self._normalize_required_text(raw_value, field_name="name")
                if field.name != new_value:
                    field.name = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "section":
                new_value = self._normalize_optional_text(raw_value)
                if field.section != new_value:
                    field.section = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "variety":
                variety_model = self._get_variety_by_name(session, str(raw_value))
                if field.variety_id != variety_model.id:
                    field.variety_id = variety_model.id
                    changed_keys.add(field_key)
                continue

            if field_key == "planting_year":
                new_value = int(raw_value)
                if field.planting_year != new_value:
                    field.planting_year = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "reference_provider":
                new_value = self._normalize_required_text(raw_value, field_name="reference_provider")
                if field.reference_provider != new_value:
                    field.reference_provider = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "reference_station":
                new_value = self._normalize_required_text(raw_value, field_name="reference_station")
                if field.reference_station != new_value:
                    field.reference_station = new_value
                    changed_keys.add(field_key)
                continue

            if field_key in {"soil_type", "soil_weight"}:
                new_value = self._normalize_optional_text(raw_value)
                if getattr(field, field_key) != new_value:
                    setattr(field, field_key, new_value)
                    changed_keys.add(field_key)
                continue

            if field_key in {
                "humus_pct",
                "effective_root_depth_cm",
                "p_allowable",
                "drip_distance",
                "drip_discharge",
                "tree_strip_width",
            }:
                new_value = None if raw_value is None else float(raw_value)
                if getattr(field, field_key) != new_value:
                    setattr(field, field_key, new_value)
                    changed_keys.add(field_key)
                continue

            if field_key == "area":
                new_value = float(raw_value)
                if field.area != new_value:
                    field.area = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "tree_count":
                new_value = None if raw_value is None else int(raw_value)
                if field.tree_count != new_value:
                    field.tree_count = new_value
                    changed_keys.add(field_key)
                continue

            if field_key in {"tree_height", "row_distance", "tree_distance", "running_metre"}:
                new_value = None if raw_value is None else float(raw_value)
                if getattr(field, field_key) != new_value:
                    setattr(field, field_key, new_value)
                    changed_keys.add(field_key)
                continue

            if field_key == "herbicide_free":
                new_value = None if raw_value is None else bool(raw_value)
                if field.herbicide_free != new_value:
                    field.herbicide_free = new_value
                    changed_keys.add(field_key)
                continue

            if field_key == "active":
                new_active = bool(raw_value)
                old_active = field.active
                if new_active != old_active:
                    if new_active:
                        field.valid_to = None
                    else:
                        today = datetime.date.today()
                        field.valid_to = today if today >= field.valid_from else field.valid_from
                    changed_keys.add(field_key)

        return changed_keys

    def get_by_id(self, session: Session, field_id: int) -> models.Field | None:
        return self._query(session).filter(models.Field.id == field_id).one_or_none()

    def list_all(self, session: Session) -> list[models.Field]:
        return self._query(session).order_by(models.Field.name, models.Field.section, models.Field.planting_year).all()

    def create(
        self,
        session: Session,
        *,
        group: str,
        name: str,
        variety: str,
        planting_year: int,
        reference_provider: str,
        reference_station: str,
        soil_type: str | None,
        soil_weight: str | None,
        humus_pct: float | None,
        area: float,
        effective_root_depth_cm: float | None,
        p_allowable: float | None,
        drip_distance: float | None,
        drip_discharge: float | None,
        tree_strip_width: float | None,
        section: str | None = None,
        tree_count: int | None = None,
        tree_height: float | None = None,
        row_distance: float | None = None,
        tree_distance: float | None = None,
        running_metre: float | None = None,
        herbicide_free: bool | None = None,
        active: bool = True,
    ) -> models.Field:
        variety_model = self._get_variety_by_name(session, variety)
        today = datetime.date.today()

        field = models.Field(
            group=self._normalize_required_text(group, field_name="group"),
            name=self._normalize_required_text(name, field_name="name"),
            section=self._normalize_optional_text(section),
            variety_id=variety_model.id,
            planting_year=int(planting_year),
            area=float(area),
            tree_count=None if tree_count is None else int(tree_count),
            tree_height=None if tree_height is None else float(tree_height),
            row_distance=None if row_distance is None else float(row_distance),
            tree_distance=None if tree_distance is None else float(tree_distance),
            running_metre=None if running_metre is None else float(running_metre),
            herbicide_free=None if herbicide_free is None else bool(herbicide_free),
            valid_from=today,
            valid_to=None if active else today,
            reference_provider=self._normalize_required_text(reference_provider, field_name="reference_provider"),
            reference_station=self._normalize_required_text(reference_station, field_name="reference_station"),
            soil_type=self._normalize_optional_text(soil_type),
            soil_weight=self._normalize_optional_text(soil_weight),
            humus_pct=None if humus_pct is None else float(humus_pct),
            effective_root_depth_cm=None if effective_root_depth_cm is None else float(effective_root_depth_cm),
            p_allowable=None if p_allowable is None else float(p_allowable),
            drip_distance=None if drip_distance is None else float(drip_distance),
            drip_discharge=None if drip_discharge is None else float(drip_discharge),
            tree_strip_width=None if tree_strip_width is None else float(tree_strip_width),
        )
        session.add(field)
        session.flush()
        logger.debug("Added new field %s", field)
        return self.get_by_id(session, field.id) or field

    def update(self, session: Session, field_id: int, updates: dict[str, Any]) -> tuple[models.Field, set[str]]:
        existing_field = self.get_by_id(session, field_id)
        if existing_field is None:
            raise ValueError(f"Could not find any field with id {field_id}")

        changed_keys = self._apply_updates(session, existing_field, updates)
        if not changed_keys:
            logger.debug("No changes for field %s; skipping update", existing_field)
            return existing_field, changed_keys

        session.flush()
        return self.get_by_id(session, field_id) or existing_field, changed_keys

    def replant(
        self,
        session: Session,
        field_id: int,
        *,
        valid_from: datetime.date,
        updates: dict[str, Any],
    ) -> tuple[models.Field, set[str]]:
        existing_field = self.get_by_id(session, field_id)
        if existing_field is None:
            raise ValueError(f"Could not find any field with id {field_id}")

        if isinstance(valid_from, str):
            valid_from = datetime.date.fromisoformat(valid_from)

        if valid_from <= existing_field.valid_from:
            raise ValueError(
                f"valid_from {valid_from.isoformat()} must be after the current record start {existing_field.valid_from.isoformat()}"
            )

        if existing_field.valid_to is not None and valid_from > existing_field.valid_to:
            raise ValueError(
                f"valid_from {valid_from.isoformat()} cannot be after the current record end {existing_field.valid_to.isoformat()}"
            )

        existing_field.valid_to = valid_from - datetime.timedelta(days=1)

        replacement = models.Field(
            group=existing_field.group,
            name=existing_field.name,
            section=existing_field.section,
            variety_id=existing_field.variety_id,
            planting_year=existing_field.planting_year,
            area=existing_field.area,
            tree_count=existing_field.tree_count,
            tree_height=existing_field.tree_height,
            row_distance=existing_field.row_distance,
            tree_distance=existing_field.tree_distance,
            running_metre=existing_field.running_metre,
            herbicide_free=existing_field.herbicide_free,
            valid_from=valid_from,
            valid_to=None,
            reference_provider=existing_field.reference_provider,
            reference_station=existing_field.reference_station,
            soil_type=existing_field.soil_type,
            soil_weight=existing_field.soil_weight,
            humus_pct=existing_field.humus_pct,
            effective_root_depth_cm=existing_field.effective_root_depth_cm,
            p_allowable=existing_field.p_allowable,
            drip_distance=existing_field.drip_distance,
            drip_discharge=existing_field.drip_discharge,
            tree_strip_width=existing_field.tree_strip_width,
        )
        session.add(replacement)
        changed_keys = self._apply_updates(session, replacement, updates)
        replacement.valid_from = valid_from
        replacement.valid_to = None
        changed_keys.add("valid_from")

        session.flush()
        logger.debug("Created replanted field %s from source %s", replacement, existing_field)
        return self.get_by_id(session, replacement.id) or replacement, changed_keys

    def delete(self, session: Session, field_id: int) -> bool:
        field = self.get_by_id(session, field_id)
        if field is None:
            return False
        session.delete(field)
        return True
