import datetime
import logging
from typing import Any

from sqlalchemy.orm import Session, selectinload

from .. import models
from .fields import FieldRepository

logger = logging.getLogger(__name__)


class PlantingRepository:
    UPDATE_ALLOWLIST = {"variety", "valid_from", "valid_to"}

    def __init__(self, field_repository: FieldRepository) -> None:
        self._fields = field_repository

    def _query(self, session: Session):
        return session.query(models.Planting).options(
            selectinload(models.Planting.variety),
            selectinload(models.Planting.sections),
        )

    def _get_variety_by_name(self, session: Session, variety_name: str) -> models.Variety:
        variety = (
            session.query(models.Variety)
            .filter(models.Variety.name == str(variety_name).strip())
            .one_or_none()
        )
        if variety is None:
            raise ValueError(
                f"Unknown variety '{variety_name}'. Create the variety master data before assigning it to a planting."
            )
        return variety

    def _normalize_date(self, value: Any, *, field_name: str) -> datetime.date | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime.date):
            return value
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"Expected ISO date for '{field_name}', got {value!r}") from exc

    def get_by_id(self, session: Session, planting_id: int) -> models.Planting | None:
        return self._query(session).filter(models.Planting.id == planting_id).one_or_none()

    def list_for_field(self, session: Session, field_id: int) -> list[models.Planting]:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found")
        return self._query(session).filter(models.Planting.field_id == field_id).order_by(models.Planting.valid_from).all()

    def create(
        self,
        session: Session,
        *,
        field_id: int,
        variety: str,
        valid_from: datetime.date,
        valid_to: datetime.date | None = None,
    ) -> models.Planting:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found")

        planting = models.Planting(
            field_id=field_id,
            variety_id=self._get_variety_by_name(session, variety).id,
            valid_from=self._normalize_date(valid_from, field_name="valid_from"),
            valid_to=self._normalize_date(valid_to, field_name="valid_to"),
        )
        session.add(planting)
        session.flush()
        logger.debug("Created new planting %s", planting)
        return self.get_by_id(session, planting.id) or planting

    def update(self, session: Session, planting_id: int, updates: dict[str, Any]) -> tuple[models.Planting, set[str]]:
        planting = self.get_by_id(session, planting_id)
        if planting is None:
            raise ValueError(f"Could not find any planting with id {planting_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_planting. Choose one of {self.UPDATE_ALLOWLIST}")

            if field_key == "variety":
                new_value = self._get_variety_by_name(session, str(raw_value)).id
                attr_name = "variety_id"
            else:
                new_value = self._normalize_date(raw_value, field_name=field_key)
                attr_name = field_key

            if getattr(planting, attr_name) != new_value:
                setattr(planting, attr_name, new_value)
                changed_keys.add(field_key)

        if planting.valid_to is not None and planting.valid_to < planting.valid_from:
            raise ValueError("valid_to must be greater than or equal to valid_from")

        if not changed_keys:
            return planting, changed_keys

        session.flush()
        return self.get_by_id(session, planting_id) or planting, changed_keys

    def delete(self, session: Session, planting_id: int) -> bool:
        planting = self.get_by_id(session, planting_id)
        if planting is None:
            return False
        session.delete(planting)
        return True
