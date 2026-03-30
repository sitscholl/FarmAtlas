import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models

logger = logging.getLogger(__name__)


class FieldRepository:
    STABLE_UPDATE_ALLOWLIST = {
        "name",
        "section",
        "reference_provider",
        "reference_station",
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
    }
    VERSIONED_UPDATE_ALLOWLIST = {
        "variety",
        "planting_year",
        "area_ha",
        "tree_count",
        "tree_height",
        "row_distance",
        "tree_distance",
        "running_metre",
        "herbicide_free",
        "active",
    }
    UPDATE_ALLOWLIST = STABLE_UPDATE_ALLOWLIST | VERSIONED_UPDATE_ALLOWLIST

    def _query(self, session: Session):
        return session.query(models.Field).options(
            selectinload(models.Field.versions).selectinload(models.FieldVersion.variety),
        )

    def _normalize_section(self, section: str | None) -> str | None:
        return None if section in (None, "") else str(section)

    def _get_variety_by_name(self, session: Session, variety_name: str) -> models.Variety:
        variety = (
            session.query(models.Variety)
            .filter(models.Variety.name == str(variety_name))
            .one_or_none()
        )
        if variety is None:
            raise ValueError(
                f"Unknown variety '{variety_name}'. Create the variety master data before assigning it to a field."
            )
        return variety

    def get_by_id(self, session: Session, field_id: int) -> models.Field | None:
        return self._query(session).filter(models.Field.id == field_id).one_or_none()

    def list_all(self, session: Session) -> list[models.Field]:
        return self._query(session).order_by(models.Field.id).all()

    def get_current_version(self, session: Session, field_id: int) -> models.FieldVersion | None:
        field = self.get_by_id(session, field_id)
        if field is None:
            return None
        return field.current_version

    def create(
        self,
        session: Session,
        *,
        name: str,
        variety: str,
        planting_year: int,
        reference_provider: str,
        reference_station: str,
        soil_type: str,
        soil_weight: str | None,
        humus_pct: float,
        area_ha: float,
        effective_root_depth_cm: float,
        p_allowable: float,
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
        field = models.Field(
            name=str(name),
            section=self._normalize_section(section),
            reference_provider=str(reference_provider),
            reference_station=str(reference_station),
            soil_type=str(soil_type),
            soil_weight=None if soil_weight in (None, "") else str(soil_weight),
            humus_pct=float(humus_pct),
            effective_root_depth_cm=float(effective_root_depth_cm),
            p_allowable=float(p_allowable),
        )
        session.add(field)
        session.flush()

        today = datetime.date.today()
        version = models.FieldVersion(
            field_id=field.id,
            variety_id=variety_model.id,
            planting_year=int(planting_year),
            area_ha=float(area_ha),
            tree_count=None if tree_count is None else int(tree_count),
            tree_height=None if tree_height is None else float(tree_height),
            row_distance=None if row_distance is None else float(row_distance),
            tree_distance=None if tree_distance is None else float(tree_distance),
            running_metre=None if running_metre is None else float(running_metre),
            herbicide_free=None if herbicide_free is None else bool(herbicide_free),
            valid_from=today,
            valid_to=None if active else today,
        )
        field.versions.append(version)
        session.flush()
        logger.debug("Added new field %s with initial version %s", field, version)
        return self.get_by_id(session, field.id) or field

    def update(self, session: Session, field_id: int, updates: dict[str, Any]) -> tuple[models.Field, set[str]]:
        existing_field = self.get_by_id(session, field_id)
        if existing_field is None:
            raise ValueError(f"Could not find any field with id {field_id}")

        current_version = existing_field.current_version
        if current_version is None:
            raise ValueError(f"Field {field_id} has no current version")

        changed_keys: set[str] = set()
        for field_key, new_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key in self.STABLE_UPDATE_ALLOWLIST:
                normalized_value = self._normalize_section(new_value) if field_key == "section" else new_value
                if getattr(existing_field, field_key) != normalized_value:
                    setattr(existing_field, field_key, normalized_value)
                    changed_keys.add(field_key)
                continue

            if field_key == "variety":
                variety_model = self._get_variety_by_name(session, str(new_value))
                if current_version.variety_id != variety_model.id:
                    current_version.variety_id = variety_model.id
                    changed_keys.add(field_key)
                continue

            if field_key == "active":
                new_active = bool(new_value)
                current_active = current_version.valid_to is None
                if current_active != new_active:
                    current_version.valid_to = None if new_active else datetime.date.today()
                    changed_keys.add(field_key)
                continue

            if getattr(existing_field, field_key) != new_value:
                setattr(current_version, field_key, new_value)
                changed_keys.add(field_key)

        if not changed_keys:
            logger.debug("No changes for field %s; skipping update", existing_field)
            return existing_field, changed_keys

        session.flush()
        return self.get_by_id(session, field_id) or existing_field, changed_keys

    def delete(self, session: Session, field_id: int) -> bool:
        field = self.get_by_id(session, field_id)
        if field is None:
            return False
        session.delete(field)
        return True
