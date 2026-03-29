import logging
from typing import Any

from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


class FieldRepository:
    UPDATE_ALLOWLIST = {
        "name",
        "section",
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
        "reference_provider",
        "reference_station",
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
    }

    def get_by_id(self, session: Session, field_id: int) -> models.Field | None:
        return (
            session.query(models.Field)
            .filter(models.Field.id == field_id)
            .one_or_none()
        )

    def list_all(self, session: Session) -> list[models.Field]:
        return session.query(models.Field).order_by(models.Field.id).all()

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
        field = models.Field(
            name=name,
            section=None if section in (None, "") else str(section),
            variety=str(variety),
            planting_year=int(planting_year),
            tree_count=None if tree_count is None else int(tree_count),
            tree_height=None if tree_height is None else float(tree_height),
            row_distance=None if row_distance is None else float(row_distance),
            tree_distance=None if tree_distance is None else float(tree_distance),
            running_metre=None if running_metre is None else float(running_metre),
            herbicide_free=None if herbicide_free is None else bool(herbicide_free),
            active=bool(active),
            reference_provider=str(reference_provider),
            reference_station=str(reference_station),
            soil_type=str(soil_type),
            soil_weight=None if soil_weight in (None, "") else str(soil_weight),
            humus_pct=float(humus_pct),
            effective_root_depth_cm=float(effective_root_depth_cm),
            area_ha=float(area_ha),
            p_allowable=float(p_allowable),
        )
        session.add(field)
        session.flush()
        logger.debug("Added new field %s to database", field)
        return field

    def update(self, session: Session, field_id: int, updates: dict[str, Any]) -> tuple[models.Field, set[str]]:
        existing_field = self.get_by_id(session, field_id)
        if existing_field is None:
            raise ValueError(f"Could not find any field with id {field_id}")

        changed_keys: set[str] = set()
        for field_key, new_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self.UPDATE_ALLOWLIST}")

            if getattr(existing_field, field_key) != new_value:
                setattr(existing_field, field_key, new_value)
                changed_keys.add(field_key)

        if not changed_keys:
            logger.debug("No changes for field %s; skipping update", existing_field)
            return existing_field, changed_keys

        session.flush()
        return existing_field, changed_keys

    def delete(self, session: Session, field_id: int) -> bool:
        field = self.get_by_id(session, field_id)
        if field is None:
            return False
        session.delete(field)
        return True
