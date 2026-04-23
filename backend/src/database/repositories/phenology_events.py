import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models
from .phenological_stages import PhenologicalStageRepository
from .sections import SectionRepository

logger = logging.getLogger(__name__)


class PhenologyEventRepository:
    UPDATE_ALLOWLIST = {"section_id", "stage_id", "date"}

    def __init__(
        self,
        section_repository: SectionRepository,
        stage_repository: PhenologicalStageRepository,
    ) -> None:
        self._sections = section_repository
        self._stages = stage_repository

    def _query(self, session: Session):
        return session.query(models.SectionPhenologyEvent).options(
            selectinload(models.SectionPhenologyEvent.section),
            selectinload(models.SectionPhenologyEvent.stage),
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

    def _resolve_stage_id(self, session: Session, value: Any) -> int:
        stage_id = int(value)
        stage = self._stages.get_by_id(session, stage_id)
        if stage is None:
            raise ValueError(f"No phenological stage with id {stage_id} found")
        return stage_id

    def get_by_id(self, session: Session, event_id: int) -> models.SectionPhenologyEvent | None:
        return self._query(session).filter(models.SectionPhenologyEvent.id == event_id).one_or_none()

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
        stage_id: int,
        date: datetime.date,
    ) -> models.SectionPhenologyEvent:
        event = models.SectionPhenologyEvent(
            section_id=self._resolve_section_id(session, section_id),
            stage_id=self._resolve_stage_id(session, stage_id),
            date=self._normalize_date(date, field_name="date"),
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
            elif field_key == "stage_id":
                new_value = self._resolve_stage_id(session, raw_value)
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
