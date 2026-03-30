import logging

from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


class VarietyRepository:
    def get_by_id(self, session: Session, variety_id: int) -> models.Variety | None:
        return (
            session.query(models.Variety)
            .filter(models.Variety.id == variety_id)
            .one_or_none()
        )

    def get_by_name(self, session: Session, name: str) -> models.Variety | None:
        return (
            session.query(models.Variety)
            .filter(models.Variety.name == str(name))
            .one_or_none()
        )

    def list_all(self, session: Session) -> list[models.Variety]:
        return session.query(models.Variety).order_by(models.Variety.name).all()

    def create(
        self,
        session: Session,
        *,
        name: str,
        group: str,
        nr_per_kg: float | None = None,
        kg_per_box: float | None = None,
        slope: float | None = None,
        intercept: float | None = None,
        specific_weight: float | None = None,
    ) -> models.Variety:
        variety = models.Variety(
            name=str(name).strip(),
            group=str(group).strip(),
            nr_per_kg=None if nr_per_kg is None else float(nr_per_kg),
            kg_per_box=None if kg_per_box is None else float(kg_per_box),
            slope=None if slope is None else float(slope),
            intercept=None if intercept is None else float(intercept),
            specific_weight=None if specific_weight is None else float(specific_weight),
        )
        session.add(variety)
        session.flush()
        logger.debug("Added new variety %s to database", variety.name)
        return variety
