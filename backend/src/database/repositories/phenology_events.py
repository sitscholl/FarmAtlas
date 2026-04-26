import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models
from ...domain.phenology import require_phenological_stage
from .sections import SectionRepository

logger = logging.getLogger(__name__)


class PhenologyEventRepository:
    UPDATE_ALLOWLIST = {"section_id", "stage_code", "date"}

    def __init__(
        self,
        section_repository: SectionRepository,
    ) -> None:
        self._sections = section_repository

    def _query(self, session: Session):
        return session.query(models.SectionPhenologyEvent).options(
            selectinload(models.SectionPhenologyEvent.section),
        )

    def _normalize_date(self, value: Any, *, field_name: str) -> datetime.date:
        if isinstance(value, datetime.date):
            return value
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"Expected ISO date for '{field_name}', got {value!r}") from exc

    def _resolve_section_id(self, session: Session, value: Any) -> int:
        section_id = int(value)
        section = self._sections.get_by_id(session, section_id)
        if section is None:
            raise ValueError(f"No section with id {section_id} found")
        return section_id

    def _resolve_stage_code(self, value: Any) -> str:
        stage_code = str(value).strip().upper()
        require_phenological_stage(stage_code)
        return stage_code

    def get_by_id(self, session: Session, event_id: int) -> models.SectionPhenologyEvent | None:
        return self._query(session).filter(models.SectionPhenologyEvent.id == event_id).one_or_none()

    def get_by_section_stage_year(
        self,
        session: Session,
        *,
        section_id: int,
        stage_code: str,
        year: int,
    ) -> models.SectionPhenologyEvent | None:
        return (
            self._query(session)
            .filter(
                models.SectionPhenologyEvent.section_id == section_id,
                models.SectionPhenologyEvent.stage_code == stage_code,
                models.SectionPhenologyEvent.year == year,
            )
            .one_or_none()
        )

    def list_for_section(self, session: Session, section_id: int) -> list[models.SectionPhenologyEvent]:
        section = self._sections.get_by_id(session, section_id)
        if section is None:
            raise ValueError(f"No section with id {section_id} found")
        return (
            self._query(session)
            .filter(models.SectionPhenologyEvent.section_id == section_id)
            .order_by(models.SectionPhenologyEvent.date, models.SectionPhenologyEvent.id)
            .all()
        )

    def create(
        self,
        session: Session,
        *,
        section_id: int,
        stage_code: str,
        date: datetime.date,
    ) -> models.SectionPhenologyEvent:
        normalized_date = self._normalize_date(date, field_name="date")
        resolved_section_id = self._resolve_section_id(session, section_id)
        resolved_stage_code = self._resolve_stage_code(stage_code)
        existing_event = self.get_by_section_stage_year(
            session,
            section_id=resolved_section_id,
            stage_code=resolved_stage_code,
            year=normalized_date.year,
        )

        if existing_event is not None:
            if existing_event.date != normalized_date:
                existing_event.date = normalized_date
                existing_event.year = normalized_date.year
                session.flush()
                logger.debug("Replaced phenology event %s", existing_event)
            return self.get_by_id(session, existing_event.id) or existing_event

        event = models.SectionPhenologyEvent(
            section_id=resolved_section_id,
            stage_code=resolved_stage_code,
            date=normalized_date,
            year=normalized_date.year,
        )
        session.add(event)
        session.flush()
        logger.debug("Created new phenology event %s", event)
        return self.get_by_id(session, event.id) or event

    def update(
        self,
        session: Session,
        event_id: int,
        updates: dict[str, Any],
    ) -> tuple[models.SectionPhenologyEvent, set[str]]:
        event = self.get_by_id(session, event_id)
        if event is None:
            raise ValueError(f"Could not find any phenology event with id {event_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(
                    f"Invalid key {field_key} in update_phenology_event. "
                    f"Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if field_key == "section_id":
                new_value = self._resolve_section_id(session, raw_value)
            elif field_key == "stage_code":
                new_value = self._resolve_stage_code(raw_value)
            elif field_key == "date":
                new_value = self._normalize_date(raw_value, field_name="date")
            else:
                raise ValueError(
                    f"Invalid key {field_key} in update_phenology_event. "
                    f"Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if getattr(event, field_key) != new_value:
                setattr(event, field_key, new_value)
                changed_keys.add(field_key)
                if field_key == "date":
                    event.year = new_value.year
                    changed_keys.add("year")

        if not changed_keys:
            return event, changed_keys

        session.flush()
        return self.get_by_id(session, event_id) or event, changed_keys

    def delete(self, session: Session, event_id: int) -> bool:
        event = self.get_by_id(session, event_id)
        if event is None:
            return False
        session.delete(event)
        session.flush()
        return True
