import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from .. import models
from .plantings import PlantingRepository

logger = logging.getLogger(__name__)


class SectionRepository:
    UPDATE_ALLOWLIST = {
        "name",
        "planting_year",
        "area",
        "tree_count",
        "tree_height",
        "row_distance",
        "tree_distance",
        "running_metre",
        "herbicide_free",
        "valid_from",
        "valid_to",
    }

    def __init__(self, planting_repository: PlantingRepository) -> None:
        self._plantings = planting_repository

    def _normalize_required_text(self, value: Any, *, field_name: str) -> str:
        text = str(value).strip()
        if text == "":
            raise ValueError(f"Expected a non-empty value for '{field_name}'")
        return text

    def _normalize_date(self, value: Any, *, field_name: str) -> datetime.date | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime.date):
            return value
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"Expected ISO date for '{field_name}', got {value!r}") from exc

    def get_by_id(self, session: Session, section_id: int) -> models.Section | None:
        return session.query(models.Section).filter(models.Section.id == section_id).one_or_none()

    def list_for_planting(self, session: Session, planting_id: int) -> list[models.Section]:
        planting = self._plantings.get_by_id(session, planting_id)
        if planting is None:
            raise ValueError(f"No planting with id {planting_id} found")
        return (
            session.query(models.Section)
            .filter(models.Section.planting_id == planting_id)
            .order_by(models.Section.valid_from, models.Section.name)
            .all()
        )

    def create(
        self,
        session: Session,
        *,
        planting_id: int,
        name: str,
        planting_year: int,
        area: float,
        valid_from: datetime.date,
        valid_to: datetime.date | None = None,
        tree_count: int | None = None,
        tree_height: float | None = None,
        row_distance: float | None = None,
        tree_distance: float | None = None,
        running_metre: float | None = None,
        herbicide_free: bool | None = None,
    ) -> models.Section:
        planting = self._plantings.get_by_id(session, planting_id)
        if planting is None:
            raise ValueError(f"No planting with id {planting_id} found")

        section = models.Section(
            planting_id=planting_id,
            name=self._normalize_required_text(name, field_name="name"),
            planting_year=int(planting_year),
            area=float(area),
            tree_count=None if tree_count is None else int(tree_count),
            tree_height=None if tree_height is None else float(tree_height),
            row_distance=None if row_distance is None else float(row_distance),
            tree_distance=None if tree_distance is None else float(tree_distance),
            running_metre=None if running_metre is None else float(running_metre),
            herbicide_free=herbicide_free,
            valid_from=self._normalize_date(valid_from, field_name="valid_from"),
            valid_to=self._normalize_date(valid_to, field_name="valid_to"),
        )
        session.add(section)
        session.flush()
        logger.debug("Created new section %s", section)
        return self.get_by_id(session, section.id) or section

    def update(self, session: Session, section_id: int, updates: dict[str, Any]) -> tuple[models.Section, set[str]]:
        section = self.get_by_id(session, section_id)
        if section is None:
            raise ValueError(f"Could not find any section with id {section_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_section. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key == "name":
                new_value = self._normalize_required_text(raw_value, field_name="name")
            elif field_key in {"valid_from", "valid_to"}:
                new_value = self._normalize_date(raw_value, field_name=field_key)
            elif field_key == "planting_year":
                new_value = int(raw_value)
            elif field_key == "tree_count":
                new_value = None if raw_value is None else int(raw_value)
            elif field_key == "herbicide_free":
                new_value = None if raw_value is None else bool(raw_value)
            else:
                new_value = None if raw_value is None else float(raw_value)

            if getattr(section, field_key) != new_value:
                setattr(section, field_key, new_value)
                changed_keys.add(field_key)

        if section.valid_to is not None and section.valid_to < section.valid_from:
            raise ValueError("valid_to must be greater than or equal to valid_from")

        if not changed_keys:
            return section, changed_keys

        session.flush()
        return self.get_by_id(session, section_id) or section, changed_keys

    def delete(self, session: Session, section_id: int) -> bool:
        section = self.get_by_id(session, section_id)
        if section is None:
            return False
        session.delete(section)
        return True
