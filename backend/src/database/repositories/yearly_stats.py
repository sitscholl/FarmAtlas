from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models


class YearlyStatsRepository:
    UPDATE_ALLOWLIST = {
        "season_year",
        "field_id",
        "planting_id",
        "section_id",
        "thinning_hours",
        "harvest_hours",
        "filled_boxes",
        "yield_kg",
        "revenue",
        "notes",
    }

    METRIC_FIELDS = {
        "thinning_hours",
        "harvest_hours",
        "filled_boxes",
        "yield_kg",
        "revenue",
    }

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip()
        return text or None

    def _normalize_scope(
        self,
        *,
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
    ) -> tuple[int | None, int | None, int | None]:
        scope_values = [field_id, planting_id, section_id]
        if sum(value is not None for value in scope_values) != 1:
            raise ValueError("Exactly one of field_id, planting_id, or section_id is required")
        return field_id, planting_id, section_id

    def _validate_scope(
        self,
        session: Session,
        *,
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
    ) -> tuple[int | None, int | None, int | None]:
        field_id, planting_id, section_id = self._normalize_scope(
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
        )
        if field_id is not None and session.get(models.Field, field_id) is None:
            raise ValueError(f"No field with id {field_id} found")
        if planting_id is not None and session.get(models.Planting, planting_id) is None:
            raise ValueError(f"No planting with id {planting_id} found")
        if section_id is not None and session.get(models.Section, section_id) is None:
            raise ValueError(f"No section with id {section_id} found")
        return field_id, planting_id, section_id

    def _apply_values(self, stats: models.YearlyStats, values: dict[str, Any]) -> None:
        for field_key, raw_value in values.items():
            if field_key in self.METRIC_FIELDS:
                setattr(stats, field_key, None if raw_value is None else float(raw_value))
            elif field_key == "season_year":
                setattr(stats, field_key, int(raw_value))
            elif field_key == "notes":
                setattr(stats, field_key, self._normalize_optional_text(raw_value))
            else:
                setattr(stats, field_key, raw_value)

    def get_by_id(self, session: Session, stats_id: int) -> models.YearlyStats | None:
        return session.query(models.YearlyStats).filter(models.YearlyStats.id == stats_id).one_or_none()

    def list_stats(
        self,
        session: Session,
        *,
        season_year: int | None = None,
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
    ) -> list[models.YearlyStats]:
        query = session.query(models.YearlyStats)
        if season_year is not None:
            query = query.filter(models.YearlyStats.season_year == int(season_year))
        if field_id is not None:
            query = query.filter(models.YearlyStats.field_id == int(field_id))
        if planting_id is not None:
            query = query.filter(models.YearlyStats.planting_id == int(planting_id))
        if section_id is not None:
            query = query.filter(models.YearlyStats.section_id == int(section_id))
        return query.order_by(models.YearlyStats.season_year, models.YearlyStats.id).all()

    def list_for_field(
        self,
        session: Session,
        *,
        field_id: int,
        season_years: list[int] | None = None,
    ) -> list[models.YearlyStats]:
        field = session.get(models.Field, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found")

        planting_ids = [
            planting_id
            for planting_id, in session.query(models.Planting.id).filter(models.Planting.field_id == field_id).all()
        ]
        section_ids = [
            section_id
            for section_id, in (
                session.query(models.Section.id)
                .join(models.Planting, models.Section.planting_id == models.Planting.id)
                .filter(models.Planting.field_id == field_id)
                .all()
            )
        ]
        query = session.query(models.YearlyStats).filter(
            or_(
                models.YearlyStats.field_id == field_id,
                models.YearlyStats.planting_id.in_(planting_ids) if planting_ids else False,
                models.YearlyStats.section_id.in_(section_ids) if section_ids else False,
            )
        )
        if season_years is not None:
            query = query.filter(models.YearlyStats.season_year.in_([int(year) for year in season_years]))
        return query.order_by(models.YearlyStats.season_year, models.YearlyStats.id).all()

    def create(
        self,
        session: Session,
        *,
        season_year: int,
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
        thinning_hours: float | None = None,
        harvest_hours: float | None = None,
        filled_boxes: float | None = None,
        yield_kg: float | None = None,
        revenue: float | None = None,
        notes: str | None = None,
    ) -> models.YearlyStats:
        field_id, planting_id, section_id = self._validate_scope(
            session,
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
        )
        stats = models.YearlyStats(
            season_year=int(season_year),
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
            thinning_hours=None if thinning_hours is None else float(thinning_hours),
            harvest_hours=None if harvest_hours is None else float(harvest_hours),
            filled_boxes=None if filled_boxes is None else float(filled_boxes),
            yield_kg=None if yield_kg is None else float(yield_kg),
            revenue=None if revenue is None else float(revenue),
            notes=self._normalize_optional_text(notes),
        )
        session.add(stats)
        session.flush()
        return self.get_by_id(session, stats.id) or stats

    def update(self, session: Session, stats_id: int, updates: dict[str, Any]) -> models.YearlyStats:
        stats = self.get_by_id(session, stats_id)
        if stats is None:
            raise ValueError(f"Could not find any yearly stats with id {stats_id}")

        pending_scope = {
            "field_id": stats.field_id,
            "planting_id": stats.planting_id,
            "section_id": stats.section_id,
        }
        normalized_updates: dict[str, Any] = {}
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_yearly_stats")
            if field_key in pending_scope:
                pending_scope[field_key] = None if raw_value is None else int(raw_value)
            else:
                normalized_updates[field_key] = raw_value

        field_id, planting_id, section_id = self._validate_scope(session, **pending_scope)
        stats.field_id = field_id
        stats.planting_id = planting_id
        stats.section_id = section_id
        self._apply_values(stats, normalized_updates)
        session.flush()
        return self.get_by_id(session, stats_id) or stats

    def delete(self, session: Session, stats_id: int) -> bool:
        stats = self.get_by_id(session, stats_id)
        if stats is None:
            return False
        session.delete(stats)
        return True
