from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ..database.db import Database
from ..database import models


COUNT_METRIC_PREFIX = "count."
YEARLY_METRICS = {
    "yield_kg": {"label": "Yield", "unit": "kg"},
    "revenue": {"label": "Revenue", "unit": "currency"},
}


@dataclass(frozen=True)
class _ScopedMean:
    value: float
    source_scope: str
    survey_ids: frozenset[int]
    sample_count: int
    sample_counts_by_survey: dict[int, int]


class ProductionSummaryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _survey_sample_mean(self, surveys: list[models.FruitCountSurvey], source_scope: str) -> _ScopedMean | None:
        sample_counts_by_survey = {
            survey.id: len(survey.samples)
            for survey in surveys
            if survey.include_in_aggregation and survey.samples
        }
        samples = [
            sample.apple_count
            for survey in surveys
            if survey.id in sample_counts_by_survey
            for sample in survey.samples
        ]
        if not samples:
            return None
        return _ScopedMean(
            value=sum(samples) / len(samples),
            source_scope=source_scope,
            survey_ids=frozenset(sample_counts_by_survey),
            sample_count=len(samples),
            sample_counts_by_survey=sample_counts_by_survey,
        )

    def _weighted_mean(self, values: list[tuple[float, float | None]]) -> float | None:
        weighted_values = [(value, weight) for value, weight in values if weight is not None and weight > 0]
        if weighted_values:
            total_weight = sum(weight for _, weight in weighted_values)
            return sum(value * weight for value, weight in weighted_values) / total_weight
        if values:
            return sum(value for value, _ in values) / len(values)
        return None

    def _percent_change(self, current_value: float | None, previous_value: float | None) -> float | None:
        if current_value is None or previous_value in (None, 0):
            return None
        return ((current_value - previous_value) / previous_value) * 100

    def _empty_source_mix(self) -> dict[str, int]:
        return {"section": 0, "planting": 0, "field": 0, "missing": 0}

    def _index_count_surveys(
        self,
        surveys: list[models.FruitCountSurvey],
    ) -> tuple[dict[tuple[str, int, int, str], list[models.FruitCountSurvey]], list[str]]:
        by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]] = defaultdict(list)
        timing_codes: set[str] = set()
        for survey in surveys:
            timing_codes.add(survey.timing_code)
            if survey.section_id is not None:
                by_scope[("section", survey.section_id, survey.season_year, survey.timing_code)].append(survey)
            elif survey.planting_id is not None:
                by_scope[("planting", survey.planting_id, survey.season_year, survey.timing_code)].append(survey)
            elif survey.field_id is not None:
                by_scope[("field", survey.field_id, survey.season_year, survey.timing_code)].append(survey)
        return by_scope, sorted(timing_codes)

    def _effective_section_count(
        self,
        *,
        field_id: int,
        planting_id: int,
        section_id: int,
        season_year: int,
        timing_code: str,
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
    ) -> _ScopedMean | None:
        for source_scope, scope_id in (
            ("section", section_id),
            ("planting", planting_id),
            ("field", field_id),
        ):
            surveys = surveys_by_scope.get((source_scope, scope_id, season_year, timing_code), [])
            mean = self._survey_sample_mean(surveys, source_scope)
            if mean is not None:
                return mean
        return None

    def _planting_count_metric(
        self,
        *,
        field: models.Field,
        planting: models.Planting,
        season_year: int,
        timing_code: str,
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
    ) -> dict[str, Any]:
        values: list[tuple[float, float | None]] = []
        source_mix = self._empty_source_mix()
        survey_ids: set[int] = set()
        sample_counts_by_survey: dict[int, int] = {}
        for section in planting.sections:
            effective = self._effective_section_count(
                field_id=field.id,
                planting_id=planting.id,
                section_id=section.id,
                season_year=season_year,
                timing_code=timing_code,
                surveys_by_scope=surveys_by_scope,
            )
            if effective is None:
                source_mix["missing"] += 1
                continue
            source_mix[effective.source_scope] += 1
            survey_ids.update(effective.survey_ids)
            sample_counts_by_survey.update(effective.sample_counts_by_survey)
            values.append((effective.value, None if section.tree_count is None else float(section.tree_count)))

        return {
            "value": self._weighted_mean(values),
            "source_scope": "mixed" if sum(1 for key in ("section", "planting", "field") if source_mix[key] > 0) > 1 else next(
                (key for key in ("section", "planting", "field") if source_mix[key] > 0),
                None,
            ),
            "source_mix": source_mix,
            "sample_tree_count": sum(sample_counts_by_survey.values()) if survey_ids else 0,
            "survey_count": len(survey_ids),
        }

    def _index_yearly_stats(
        self,
        stats: list[models.YearlyStats],
    ) -> dict[tuple[str, int, int], models.YearlyStats]:
        indexed: dict[tuple[str, int, int], models.YearlyStats] = {}
        for item in stats:
            if item.section_id is not None:
                indexed[("section", item.section_id, item.season_year)] = item
            elif item.planting_id is not None:
                indexed[("planting", item.planting_id, item.season_year)] = item
            elif item.field_id is not None:
                indexed[("field", item.field_id, item.season_year)] = item
        return indexed

    def _planting_yearly_metric(
        self,
        *,
        planting: models.Planting,
        season_year: int,
        metric_code: str,
        stats_by_scope: dict[tuple[str, int, int], models.YearlyStats],
    ) -> dict[str, Any]:
        direct = stats_by_scope.get(("planting", planting.id, season_year))
        if direct is not None:
            value = getattr(direct, metric_code)
            if value is not None:
                return {"value": float(value), "source_scope": "planting", "source_mix": {"planting": 1}}

        section_values = []
        for section in planting.sections:
            section_stats = stats_by_scope.get(("section", section.id, season_year))
            if section_stats is None:
                continue
            value = getattr(section_stats, metric_code)
            if value is not None:
                section_values.append(float(value))
        if section_values:
            return {
                "value": sum(section_values),
                "source_scope": "section",
                "source_mix": {"section": len(section_values), "missing": len(planting.sections) - len(section_values)},
            }
        return {"value": None, "source_scope": None, "source_mix": {"missing": len(planting.sections)}}

    def _history_values(
        self,
        *,
        years: list[int],
        metric_code: str,
        metric_kind: str,
        field: models.Field,
        planting: models.Planting,
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
        stats_by_scope: dict[tuple[str, int, int], models.YearlyStats],
    ) -> list[dict[str, Any]]:
        history = []
        for year in years:
            if metric_kind == "count":
                count_value = self._planting_count_metric(
                    field=field,
                    planting=planting,
                    season_year=year,
                    timing_code=metric_code.removeprefix(COUNT_METRIC_PREFIX),
                    surveys_by_scope=surveys_by_scope,
                )
                value = count_value["value"]
                source_scope = count_value["source_scope"]
                source_mix = count_value["source_mix"]
            else:
                yearly_value = self._planting_yearly_metric(
                    planting=planting,
                    season_year=year,
                    metric_code=metric_code,
                    stats_by_scope=stats_by_scope,
                )
                value = yearly_value["value"]
                source_scope = yearly_value["source_scope"]
                source_mix = yearly_value["source_mix"]
            history.append(
                {
                    "season_year": year,
                    "value": value,
                    "source_scope": source_scope,
                    "source_mix": source_mix,
                }
            )
        return history

    def get_planting_year_comparison(
        self,
        *,
        season_year: int,
        history_years: int = 5,
        field_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        if history_years < 2:
            raise ValueError("history_years must be at least 2")

        current_year = int(season_year)
        years = list(range(current_year - int(history_years) + 1, current_year + 1))
        previous_year = current_year - 1

        rows: list[dict[str, Any]] = []
        metric_definitions: dict[str, dict[str, str]] = {
            metric_code: {"metric_code": metric_code, **definition}
            for metric_code, definition in YEARLY_METRICS.items()
        }

        with self.db.session_scope() as session:
            fields = self.db.fields.list_all(session)
            if field_ids is not None:
                requested_ids = {int(field_id) for field_id in field_ids}
                fields = [field for field in fields if field.id in requested_ids]
                missing_ids = requested_ids - {field.id for field in fields}
                if missing_ids:
                    raise ValueError(f"Unknown field ids: {sorted(missing_ids)}")

            field_data = []
            for field in fields:
                surveys = self.db.fruit_counts.list_for_field(
                    session,
                    field_id=field.id,
                    season_years=years,
                    include_excluded=False,
                )
                stats = self.db.yearly_stats.list_for_field(session, field_id=field.id, season_years=years)
                surveys_by_scope, timing_codes = self._index_count_surveys(surveys)
                stats_by_scope = self._index_yearly_stats(stats)
                field_data.append((field, surveys_by_scope, stats_by_scope))

                for timing_code in timing_codes:
                    metric_code = f"{COUNT_METRIC_PREFIX}{timing_code}"
                    metric_definitions[metric_code] = {
                        "metric_code": metric_code,
                        "label": f"Count {timing_code}",
                        "unit": "apples/tree",
                    }

            sorted_metric_codes = sorted(metric_definitions)
            for field, surveys_by_scope, stats_by_scope in field_data:
                for planting in field.plantings:
                    metrics = []
                    for metric_code in sorted_metric_codes:
                        metric_kind = "count" if metric_code.startswith(COUNT_METRIC_PREFIX) else "yearly"
                        history = self._history_values(
                            years=years,
                            metric_code=metric_code,
                            metric_kind=metric_kind,
                            field=field,
                            planting=planting,
                            surveys_by_scope=surveys_by_scope,
                            stats_by_scope=stats_by_scope,
                        )
                        values_by_year = {entry["season_year"]: entry for entry in history}
                        current = values_by_year[current_year]
                        previous = values_by_year.get(previous_year)
                        metrics.append(
                            {
                                **metric_definitions[metric_code],
                                "current_value": current["value"],
                                "previous_value": None if previous is None else previous["value"],
                                "percent_change": self._percent_change(
                                    current["value"],
                                    None if previous is None else previous["value"],
                                ),
                                "current_source_scope": current["source_scope"],
                                "current_source_mix": current["source_mix"],
                                "history": history,
                            }
                        )

                    rows.append(
                        {
                            "field_id": field.id,
                            "field_group": field.group,
                            "field_name": field.name,
                            "planting_id": planting.id,
                            "variety": planting.variety.name,
                            "valid_from": planting.valid_from,
                            "valid_to": planting.valid_to,
                            "active": planting.active,
                            "section_count": len(planting.sections),
                            "area": planting.area,
                            "tree_count": planting.tree_count,
                            "metrics": metrics,
                        }
                    )

        return {
            "season_year": current_year,
            "previous_year": previous_year,
            "history_years": years,
            "metrics": sorted(metric_definitions.values(), key=lambda item: item["metric_code"]),
            "rows": rows,
        }
