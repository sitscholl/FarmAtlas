import logging
from typing import Any

from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


class PhenologicalStageRepository:
    UPDATE_ALLOWLIST = {"name", "kc"}

    def _normalize_name(self, value: Any) -> str:
        name = str(value).strip()
        if name == "":
            raise ValueError("Expected a non-empty value for 'name'")
        return name

    def _normalize_kc(self, value: Any) -> float:
        kc = float(value)
        if kc < 0:
            raise ValueError("kc must be greater than or equal to 0")
        return kc

    def get_by_id(self, session: Session, stage_id: int) -> models.PhenologicalStage | None:
        return (
            session.query(models.PhenologicalStage)
            .filter(models.PhenologicalStage.id == stage_id)
            .one_or_none()
        )

    def list_all(self, session: Session) -> list[models.PhenologicalStage]:
        return session.query(models.PhenologicalStage).order_by(models.PhenologicalStage.name).all()

    def create(
        self,
        session: Session,
        *,
        name: str,
        kc: float,
    ) -> models.PhenologicalStage:
        stage = models.PhenologicalStage(
            name=self._normalize_name(name),
            kc=self._normalize_kc(kc),
        )
        session.add(stage)
        session.flush()
        logger.debug("Created new phenological stage %s", stage)
        return self.get_by_id(session, stage.id) or stage

    def update(
        self,
        session: Session,
        stage_id: int,
        updates: dict[str, Any],
    ) -> tuple[models.PhenologicalStage, set[str]]:
        stage = self.get_by_id(session, stage_id)
        if stage is None:
            raise ValueError(f"Could not find any phenological stage with id {stage_id}")

        changed_keys: set[str] = set()
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(
                    f"Invalid key {field_key} in update_phenological_stage. "
                    f"Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if field_key == "name":
                new_value = self._normalize_name(raw_value)
            elif field_key == "kc":
                new_value = self._normalize_kc(raw_value)
            else:
                raise ValueError(
                    f"Invalid key {field_key} in update_phenological_stage. "
                    f"Choose one of {self.UPDATE_ALLOWLIST}"
                )

            if getattr(stage, field_key) != new_value:
                setattr(stage, field_key, new_value)
                changed_keys.add(field_key)

        if not changed_keys:
            return stage, changed_keys

        session.flush()
        return self.get_by_id(session, stage_id) or stage, changed_keys

    def delete(self, session: Session, stage_id: int) -> bool:
        stage = self.get_by_id(session, stage_id)
        if stage is None:
            return False
        session.delete(stage)
        session.flush()
        return True
