import datetime
import logging
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from .. import models
from .fields import FieldRepository

logger = logging.getLogger(__name__)


class IrrigationRepository:
    UPDATE_ALLOWLIST = {"field_id", "date", "method", "duration", "amount"}

    def __init__(
        self,
        field_repository: FieldRepository,
    ) -> None:
        self._fields = field_repository

    def get_by_id(self, session: Session, event_id: int) -> models.Irrigation | None:
        return (
            session.query(models.Irrigation)
            .filter(models.Irrigation.id == event_id)
            .one_or_none()
        )

    def list(
        self,
        session: Session,
        *,
        field_id: int | None = None,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[models.Irrigation]:
        if start is not None:
            start = pd.Timestamp(start).date()
        if end is not None:
            end = pd.Timestamp(end).date()

        query = session.query(models.Irrigation)
        if field_id is not None:
            field = self._fields.get_by_id(session, field_id)
            if field is None:
                raise ValueError(f"No field with id {field_id} found. Cannot query irrigation event")
            query = query.filter(models.Irrigation.field_id == field_id)

        if start is not None:
            query = query.filter(models.Irrigation.date >= start)
        if end is not None:
            query = query.filter(models.Irrigation.date < end)
        return query.all()

    def get_first_for_year(self, session: Session, *, field_id: int, year: int) -> models.Irrigation | None:
        return (
            session.query(models.Irrigation)
            .filter(models.Irrigation.field_id == field_id)
            .filter(
                models.Irrigation.date >= datetime.date(year, 1, 1),
                models.Irrigation.date < datetime.date(year + 1, 1, 1),
            )
            .order_by(models.Irrigation.date.asc())
            .limit(1)
            .one_or_none()
        )

    def create(
        self,
        session: Session,
        *,
        field_id: int,
        date: datetime.date,
        method: str,
        duration: float,
        amount: float,
    ) -> models.Irrigation:
        if isinstance(date, str):
            date = pd.Timestamp(date).date()

        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id '{field_id}' found")

        event = models.Irrigation(
            field_id=field.id,
            date=date,
            method=method,
            duration=duration,
            amount=amount,
        )
        session.add(event)
        session.flush()
        logger.debug("Created new irrigation event for field %s", field)
        return event

    def update(self, session: Session, event_id: int, updates: dict[str, Any]) -> models.Irrigation:
        existing_event = self.get_by_id(session, event_id)
        if existing_event is None:
            raise ValueError(f"Could not find any irrigation event with id {event_id}")

        updated = False
        old_field_id = None
        for field_key, new_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_irriation_event. Choose one of {self.UPDATE_ALLOWLIST}")

            if getattr(existing_event, field_key) != new_value and new_value is not None:
                if field_key == "field_id":
                    new_field = self._fields.get_by_id(session, new_value)
                    if new_field is None:
                        raise ValueError(f"Invalid new field id {new_value} in update_irrigation_event.")
                    old_field_id = existing_event.field_id

                if field_key == "date":
                    new_value = pd.Timestamp(new_value).date()

                setattr(existing_event, field_key, new_value)
                updated = True

        if not updated:
            logger.debug("No changes for irrigation_event %s; skipping update", existing_event)
            return existing_event

        session.flush()
        return existing_event

    def delete(self, session: Session, event_id: int) -> bool:
        event = session.get(models.Irrigation, event_id)
        if event is None:
            return False
        session.delete(event)
        return True

    def clear_for_field(self, session: Session, field_id: int) -> int:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot clear irrigation events")

        deleted = (
            session.query(models.Irrigation)
            .filter(models.Irrigation.field_id == field_id)
            .delete(synchronize_session=False)
        )
        logger.info("Cleared %s irrigation event(s) for field %s", deleted, field_id)
        return deleted
