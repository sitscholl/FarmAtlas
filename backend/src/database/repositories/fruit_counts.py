import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from .. import models


class FruitCountRepository:
    UPDATE_ALLOWLIST = {
        "season_year",
        "date",
        "timing_code",
        "field_id",
        "planting_id",
        "section_id",
        "method",
        "observer",
        "notes",
        "include_in_aggregation",
        "quality_flag",
    }

    def _query(self, session: Session):
        return session.query(models.FruitCountSurvey).options(selectinload(models.FruitCountSurvey.samples))

    def _normalize_date(self, value: Any, *, field_name: str) -> datetime.date:
        if isinstance(value, datetime.date):
            return value
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"Expected ISO date for '{field_name}', got {value!r}") from exc

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip()
        return text or None

    def _normalize_required_text(self, value: Any, *, field_name: str) -> str:
        text = str(value).strip()
        if text == "":
            raise ValueError(f"Expected a non-empty value for '{field_name}'")
        return text

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

    def _build_samples(self, samples: list[dict[str, Any]]) -> list[models.FruitCountSample]:
        if not samples:
            raise ValueError("At least one fruit count sample is required")
        return [
            models.FruitCountSample(
                tree_label=self._normalize_optional_text(sample.get("tree_label")),
                apple_count=int(sample["apple_count"]),
                notes=self._normalize_optional_text(sample.get("notes")),
            )
            for sample in samples
        ]

    def get_by_id(self, session: Session, survey_id: int) -> models.FruitCountSurvey | None:
        return self._query(session).filter(models.FruitCountSurvey.id == survey_id).one_or_none()

    def list_surveys(
        self,
        session: Session,
        *,
        season_year: int | None = None,
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
        timing_code: str | None = None,
        include_excluded: bool = True,
    ) -> list[models.FruitCountSurvey]:
        query = self._query(session)
        if season_year is not None:
            query = query.filter(models.FruitCountSurvey.season_year == int(season_year))
        if field_id is not None:
            query = query.filter(models.FruitCountSurvey.field_id == int(field_id))
        if planting_id is not None:
            query = query.filter(models.FruitCountSurvey.planting_id == int(planting_id))
        if section_id is not None:
            query = query.filter(models.FruitCountSurvey.section_id == int(section_id))
        if timing_code is not None:
            query = query.filter(models.FruitCountSurvey.timing_code == self._normalize_required_text(timing_code, field_name="timing_code"))
        if not include_excluded:
            query = query.filter(models.FruitCountSurvey.include_in_aggregation.is_(True))
        return query.order_by(
            models.FruitCountSurvey.season_year,
            models.FruitCountSurvey.date,
            models.FruitCountSurvey.id,
        ).all()

    def list_for_field(
        self,
        session: Session,
        *,
        field_id: int,
        season_years: list[int] | None = None,
        include_excluded: bool = True,
    ) -> list[models.FruitCountSurvey]:
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
        query = self._query(session).filter(
            or_(
                models.FruitCountSurvey.field_id == field_id,
                models.FruitCountSurvey.planting_id.in_(planting_ids) if planting_ids else False,
                models.FruitCountSurvey.section_id.in_(section_ids) if section_ids else False,
            )
        )
        if season_years is not None:
            query = query.filter(models.FruitCountSurvey.season_year.in_([int(year) for year in season_years]))
        if not include_excluded:
            query = query.filter(models.FruitCountSurvey.include_in_aggregation.is_(True))
        return query.order_by(
            models.FruitCountSurvey.season_year,
            models.FruitCountSurvey.date,
            models.FruitCountSurvey.id,
        ).all()

    def create(
        self,
        session: Session,
        *,
        season_year: int,
        date: datetime.date,
        timing_code: str,
        samples: list[dict[str, Any]],
        field_id: int | None = None,
        planting_id: int | None = None,
        section_id: int | None = None,
        method: str | None = None,
        observer: str | None = None,
        notes: str | None = None,
        include_in_aggregation: bool = True,
        quality_flag: str | None = None,
    ) -> models.FruitCountSurvey:
        field_id, planting_id, section_id = self._validate_scope(
            session,
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
        )
        survey = models.FruitCountSurvey(
            season_year=int(season_year),
            date=self._normalize_date(date, field_name="date"),
            timing_code=self._normalize_required_text(timing_code, field_name="timing_code"),
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
            method=self._normalize_optional_text(method),
            observer=self._normalize_optional_text(observer),
            notes=self._normalize_optional_text(notes),
            include_in_aggregation=bool(include_in_aggregation),
            quality_flag=self._normalize_optional_text(quality_flag),
            created_at=datetime.datetime.now(),
            samples=self._build_samples(samples),
        )
        session.add(survey)
        session.flush()
        return self.get_by_id(session, survey.id) or survey

    def update(self, session: Session, survey_id: int, updates: dict[str, Any]) -> models.FruitCountSurvey:
        survey = self.get_by_id(session, survey_id)
        if survey is None:
            raise ValueError(f"Could not find any fruit count survey with id {survey_id}")

        pending_scope = {
            "field_id": survey.field_id,
            "planting_id": survey.planting_id,
            "section_id": survey.section_id,
        }
        samples = updates.pop("samples", None)
        for field_key, raw_value in updates.items():
            if field_key not in self.UPDATE_ALLOWLIST:
                raise ValueError(f"Invalid key {field_key} in update_fruit_count_survey")
            if field_key in pending_scope:
                pending_scope[field_key] = None if raw_value is None else int(raw_value)
                continue
            if field_key == "date":
                new_value = self._normalize_date(raw_value, field_name=field_key)
            elif field_key == "season_year":
                new_value = int(raw_value)
            elif field_key == "include_in_aggregation":
                new_value = bool(raw_value)
            elif field_key == "timing_code":
                new_value = self._normalize_required_text(raw_value, field_name=field_key)
            else:
                new_value = self._normalize_optional_text(raw_value)
            setattr(survey, field_key, new_value)

        field_id, planting_id, section_id = self._validate_scope(session, **pending_scope)
        survey.field_id = field_id
        survey.planting_id = planting_id
        survey.section_id = section_id
        if samples is not None:
            survey.samples = self._build_samples(samples)
        session.flush()
        return self.get_by_id(session, survey_id) or survey

    def delete(self, session: Session, survey_id: int) -> bool:
        survey = self.get_by_id(session, survey_id)
        if survey is None:
            return False
        session.delete(survey)
        return True
