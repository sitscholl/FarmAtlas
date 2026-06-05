import datetime
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from .. import models
from .sections import SectionRepository


class TreatmentRepository:
    def __init__(self, section_repository: SectionRepository) -> None:
        self._sections = section_repository

    def list_events(
        self,
        session: Session,
        *,
        source: str | None = None,
        season_year: int | None = None,
        section_id: int | None = None,
        resolution_status: str | None = None,
    ) -> list[models.TreatmentEvent]:
        query = session.query(models.TreatmentEvent).options(selectinload(models.TreatmentEvent.section))
        if source is not None:
            query = query.filter(models.TreatmentEvent.source == source)
        if season_year is not None:
            query = query.filter(models.TreatmentEvent.season_year == season_year)
        if section_id is not None:
            query = query.filter(models.TreatmentEvent.section_id == section_id)
        if resolution_status is not None:
            query = query.filter(models.TreatmentEvent.resolution_status == resolution_status)
        return query.order_by(models.TreatmentEvent.date.desc(), models.TreatmentEvent.id.desc()).all()

    def list_imports(
        self,
        session: Session,
        *,
        source: str | None = None,
        season_year: int | None = None,
    ) -> list[models.TreatmentImport]:
        query = session.query(models.TreatmentImport)
        if source is not None:
            query = query.filter(models.TreatmentImport.source == source)
        if season_year is not None:
            query = query.filter(models.TreatmentImport.season_year == season_year)
        return query.order_by(models.TreatmentImport.imported_at.desc()).all()

    def list_aliases(self, session: Session, *, source: str | None = None) -> list[models.TreatmentSectionAlias]:
        query = session.query(models.TreatmentSectionAlias).options(
            selectinload(models.TreatmentSectionAlias.section),
        )
        if source is not None:
            query = query.filter(models.TreatmentSectionAlias.source == source)
        return query.order_by(models.TreatmentSectionAlias.source, models.TreatmentSectionAlias.external_section_name).all()

    def get_alias_by_id(self, session: Session, alias_id: int) -> models.TreatmentSectionAlias | None:
        return (
            session.query(models.TreatmentSectionAlias)
            .options(selectinload(models.TreatmentSectionAlias.section))
            .filter(models.TreatmentSectionAlias.id == alias_id)
            .one_or_none()
        )

    def get_alias_map(self, session: Session, *, source: str) -> dict[str, int]:
        aliases = self.list_aliases(session, source=source)
        return {alias.external_section_name: alias.section_id for alias in aliases}

    def distinct_product_names(self, session: Session, *, source: str | None = None) -> list[str]:
        query = session.query(models.TreatmentEvent.product_name).distinct()
        if source is not None:
            query = query.filter(models.TreatmentEvent.source == source)
        return [str(value) for (value,) in query.order_by(func.lower(models.TreatmentEvent.product_name)).all()]

    def unresolved_external_section_names(
        self,
        session: Session,
        *,
        source: str | None = None,
        season_year: int | None = None,
    ) -> list[str]:
        query = (
            session.query(models.TreatmentEvent.external_section_name)
            .filter(models.TreatmentEvent.resolution_status == "unresolved")
            .distinct()
        )
        if source is not None:
            query = query.filter(models.TreatmentEvent.source == source)
        if season_year is not None:
            query = query.filter(models.TreatmentEvent.season_year == season_year)
        return [str(value) for (value,) in query.order_by(models.TreatmentEvent.external_section_name).all()]

    def replace_season_events(
        self,
        session: Session,
        *,
        source: str,
        season_year: int,
        records: Iterable[dict[str, Any]],
    ) -> int:
        session.query(models.TreatmentEvent).filter(
            models.TreatmentEvent.source == source,
            models.TreatmentEvent.season_year == season_year,
        ).delete(synchronize_session=False)

        event_models = [models.TreatmentEvent(**record) for record in records]
        if not event_models:
            return 0
        session.add_all(event_models)
        session.flush()
        return len(event_models)

    def upsert_import_summary(
        self,
        session: Session,
        *,
        source: str,
        season_year: int,
        imported_at: datetime.datetime,
        row_count: int,
        unresolved_count: int,
    ) -> models.TreatmentImport:
        existing = (
            session.query(models.TreatmentImport)
            .filter(
                models.TreatmentImport.source == source,
                models.TreatmentImport.season_year == season_year,
            )
            .one_or_none()
        )
        if existing is None:
            existing = models.TreatmentImport(
                source=source,
                season_year=season_year,
                imported_at=imported_at,
                row_count=row_count,
                unresolved_count=unresolved_count,
            )
            session.add(existing)
        else:
            existing.imported_at = imported_at
            existing.row_count = row_count
            existing.unresolved_count = unresolved_count
        session.flush()
        return existing

    def create_alias(
        self,
        session: Session,
        *,
        source: str,
        external_section_name: str,
        section_id: int,
    ) -> models.TreatmentSectionAlias:
        section = self._sections.get_by_id(session, section_id)
        if section is None:
            raise ValueError(f"No section with id {section_id} found")
        alias = models.TreatmentSectionAlias(
            source=source.strip(),
            external_section_name=external_section_name.strip(),
            section_id=section_id,
        )
        session.add(alias)
        session.flush()
        return self.get_alias_by_id(session, alias.id) or alias

    def update_alias(
        self,
        session: Session,
        alias_id: int,
        *,
        source: str,
        external_section_name: str,
        section_id: int,
    ) -> models.TreatmentSectionAlias:
        alias = self.get_alias_by_id(session, alias_id)
        if alias is None:
            raise ValueError(f"Could not find any treatment section alias with id {alias_id}")
        section = self._sections.get_by_id(session, section_id)
        if section is None:
            raise ValueError(f"No section with id {section_id} found")
        alias.source = source.strip()
        alias.external_section_name = external_section_name.strip()
        alias.section_id = section_id
        session.flush()
        return self.get_alias_by_id(session, alias_id) or alias

    def delete_alias(self, session: Session, alias_id: int) -> bool:
        alias = self.get_alias_by_id(session, alias_id)
        if alias is None:
            return False
        session.delete(alias)
        return True

    def resolve_events_for_alias(
        self,
        session: Session,
        *,
        source: str,
        external_section_name: str,
        section_id: int | None,
    ) -> int:
        updates = {
            "section_id": section_id,
            "resolution_status": "resolved" if section_id is not None else "unresolved",
        }
        return (
            session.query(models.TreatmentEvent)
            .filter(
                models.TreatmentEvent.source == source,
                models.TreatmentEvent.external_section_name == external_section_name,
            )
            .update(updates, synchronize_session=False)
        )
