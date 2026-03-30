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
        return (
            self._query(session)
            .filter(models.Field.id == field_id)
            .filter(models.Field.versions.any())
            .one_or_none()
        )

    def list_all(self, session: Session) -> list[models.Field]:
        return (
            self._query(session)
            .filter(models.Field.versions.any())
            .order_by(models.Field.id)
            .all()
        )

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
        soil_type: str | None,
        soil_weight: str | None,
        humus_pct: float | None,
        area_ha: float,
        effective_root_depth_cm: float | None,
        p_allowable: float | None,
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
            soil_type=None if soil_type in (None, "") else str(soil_type),
            soil_weight=None if soil_weight in (None, "") else str(soil_weight),
            humus_pct=None if humus_pct is None else float(humus_pct),
            effective_root_depth_cm=None if effective_root_depth_cm is None else float(effective_root_depth_cm),
            p_allowable=None if p_allowable is None else float(p_allowable),
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

        effective_from_raw = updates.pop("effective_from", None)
        effective_from = None
        if effective_from_raw is not None:
            effective_from = datetime.date.fromisoformat(str(effective_from_raw))

        changed_keys: set[str] = set()
        stable_updates: dict[str, Any] = {}
        versioned_updates: dict[str, Any] = {}
        for field_key, new_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key in self.STABLE_UPDATE_ALLOWLIST:
                if field_key in {"section", "soil_type", "soil_weight"}:
                    stable_updates[field_key] = self._normalize_section(new_value)
                else:
                    stable_updates[field_key] = new_value
                continue

            versioned_updates[field_key] = new_value

        for field_key, new_value in stable_updates.items():
            if getattr(existing_field, field_key) != new_value:
                setattr(existing_field, field_key, new_value)
                changed_keys.add(field_key)

        version_changes: dict[str, Any] = {}
        if "variety" in versioned_updates:
            variety_model = self._get_variety_by_name(session, str(versioned_updates["variety"]))
            if current_version.variety_id != variety_model.id:
                version_changes["variety_id"] = variety_model.id
                changed_keys.add("variety")

        if "active" in versioned_updates:
            new_active = bool(versioned_updates["active"])
            current_active = current_version.valid_to is None
            if current_active != new_active:
                version_changes["active"] = new_active
                changed_keys.add("active")

        for field_key in self.VERSIONED_UPDATE_ALLOWLIST - {"variety", "active"}:
            if field_key not in versioned_updates:
                continue
            new_value = versioned_updates[field_key]
            if getattr(existing_field, field_key) != new_value:
                version_changes[field_key] = new_value
                changed_keys.add(field_key)

        if not changed_keys:
            logger.debug("No changes for field %s; skipping update", existing_field)
            return existing_field, changed_keys

        if version_changes:
            effective_on = effective_from or datetime.date.today()
            if effective_on < current_version.valid_from:
                raise ValueError(
                    f"effective_from {effective_on.isoformat()} cannot be before the current version start {current_version.valid_from.isoformat()}"
                )

            replaces_current_version = effective_on > current_version.valid_from
            if replaces_current_version:
                current_version.valid_to = effective_on - datetime.timedelta(days=1)
                replacement = models.FieldVersion(
                    field_id=existing_field.id,
                    variety_id=current_version.variety_id,
                    planting_year=current_version.planting_year,
                    area_ha=current_version.area_ha,
                    tree_count=current_version.tree_count,
                    tree_height=current_version.tree_height,
                    row_distance=current_version.row_distance,
                    tree_distance=current_version.tree_distance,
                    running_metre=current_version.running_metre,
                    herbicide_free=current_version.herbicide_free,
                    valid_from=effective_on,
                    valid_to=None,
                )
                session.add(replacement)
                working_version = replacement
            else:
                working_version = current_version

            if "variety_id" in version_changes:
                working_version.variety_id = version_changes["variety_id"]
            if "planting_year" in version_changes:
                working_version.planting_year = int(version_changes["planting_year"])
            if "area_ha" in version_changes:
                working_version.area_ha = float(version_changes["area_ha"])
            if "tree_count" in version_changes:
                working_version.tree_count = None if version_changes["tree_count"] is None else int(version_changes["tree_count"])
            if "tree_height" in version_changes:
                working_version.tree_height = None if version_changes["tree_height"] is None else float(version_changes["tree_height"])
            if "row_distance" in version_changes:
                working_version.row_distance = None if version_changes["row_distance"] is None else float(version_changes["row_distance"])
            if "tree_distance" in version_changes:
                working_version.tree_distance = None if version_changes["tree_distance"] is None else float(version_changes["tree_distance"])
            if "running_metre" in version_changes:
                working_version.running_metre = None if version_changes["running_metre"] is None else float(version_changes["running_metre"])
            if "herbicide_free" in version_changes:
                working_version.herbicide_free = (
                    None if version_changes["herbicide_free"] is None else bool(version_changes["herbicide_free"])
                )
            if "active" in version_changes:
                working_version.valid_to = None if version_changes["active"] else effective_on

        session.flush()
        return self.get_by_id(session, field_id) or existing_field, changed_keys

    def delete(self, session: Session, field_id: int) -> bool:
        field = self.get_by_id(session, field_id)
        if field is None:
            return False
        session.delete(field)
        return True
