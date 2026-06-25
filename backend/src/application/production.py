from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ..database.db import Database
from ..database import models
from ..domain.validity import active_sections_for_year, planting_active_in_year


COUNT_METRIC_PREFIX = "count."
COUNT_TIMING_METRICS = (
    {
        "metric_code": "count.before_hand_thinning",
        "label": "Vor Handausdünnung",
        "unit": "apples/tree",
        "timing_codes": ("Vor Handausdünnung", "Vor HandausdÃ¼nnung"),
    },
    {
        "metric_code": "count.after_hand_thinning",
        "label": "Nach Handausdünnung",
        "unit": "apples/tree",
        "timing_codes": ("Nach Handausdünnung", "Nach HandausdÃ¼nnung"),
    },
)
YEARLY_FIELD_STATISTICS_METRICS = (
    {"metric_code": "thinning_hours", "label": "Zupfen [h]", "unit": "h"},
    {"metric_code": "yield_kg", "label": "Ertrag [kg]", "unit": "kg"},
    {"metric_code": "filled_boxes", "label": "Kisten", "unit": "boxes"},
    {"metric_code": "harvest_hours", "label": "Ernte [h]", "unit": "h"},
    {"metric_code": "revenue", "label": "Erlös [€]", "unit": "currency"},
)
FIELD_STATISTICS_METRICS = (
    *COUNT_TIMING_METRICS,
    *YEARLY_FIELD_STATISTICS_METRICS,
)


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

    def _empty_source_mix(self) -> dict[str, int]:
        return {"section": 0, "planting": 0, "field": 0, "missing": 0}

    def _planting_sections_for_year(self, planting: models.Planting, season_year: int) -> list[models.Section]:
        return active_sections_for_year(planting, season_year)

    def _planting_area_for_year(self, planting: models.Planting, season_year: int) -> float:
        return sum(float(section.area) for section in self._planting_sections_for_year(planting, season_year))

    def _planting_tree_count_for_year(self, planting: models.Planting, season_year: int) -> int | None:
        counts = [
            int(section.tree_count)
            for section in self._planting_sections_for_year(planting, season_year)
            if section.tree_count is not None
        ]
        return sum(counts) if counts else None

    def _field_area_for_year(self, field: models.Field, season_year: int) -> float:
        return sum(
            self._planting_area_for_year(planting, season_year)
            for planting in field.plantings
            if planting_active_in_year(planting, season_year)
        )

    def _missing_count_metric(self, missing_count: int) -> dict[str, Any]:
        return {
            "value": None,
            "value_per_hectare": None,
            "source_scope": None,
            "source_mix": {"missing": missing_count},
            "sample_tree_count": 0,
            "survey_count": 0,
        }

    def _missing_yearly_metric(self, missing_count: int) -> dict[str, Any]:
        return {
            "value": None,
            "value_per_hectare": None,
            "source_scope": None,
            "source_mix": {"missing": missing_count},
            "sample_tree_count": None,
            "survey_count": None,
        }

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

    def _effective_section_count_for_timing_codes(
        self,
        *,
        field_id: int,
        planting_id: int,
        section_id: int,
        season_year: int,
        timing_codes: tuple[str, ...],
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
    ) -> _ScopedMean | None:
        for source_scope, scope_id in (
            ("section", section_id),
            ("planting", planting_id),
            ("field", field_id),
        ):
            surveys = [
                survey
                for timing_code in timing_codes
                for survey in surveys_by_scope.get((source_scope, scope_id, season_year, timing_code), [])
            ]
            mean = self._survey_sample_mean(surveys, source_scope)
            if mean is not None:
                return mean
        return None

    def _planting_count_metric_for_timing_codes(
        self,
        *,
        field: models.Field,
        planting: models.Planting,
        season_year: int,
        timing_codes: tuple[str, ...],
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
    ) -> dict[str, Any]:
        active_sections = self._planting_sections_for_year(planting, season_year)
        if not planting_active_in_year(planting, season_year):
            return self._missing_count_metric(0)

        values: list[tuple[float, float | None]] = []
        source_mix = self._empty_source_mix()
        survey_ids: set[int] = set()
        sample_counts_by_survey: dict[int, int] = {}
        for section in active_sections:
            effective = self._effective_section_count_for_timing_codes(
                field_id=field.id,
                planting_id=planting.id,
                section_id=section.id,
                season_year=season_year,
                timing_codes=timing_codes,
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
            "value_per_hectare": None,
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
        field: models.Field,
        planting: models.Planting,
        season_year: int,
        metric_code: str,
        stats_by_scope: dict[tuple[str, int, int], models.YearlyStats],
    ) -> dict[str, Any]:
        active_sections = self._planting_sections_for_year(planting, season_year)
        planting_area = self._planting_area_for_year(planting, season_year)
        if not planting_active_in_year(planting, season_year):
            return self._missing_yearly_metric(0)

        direct = stats_by_scope.get(("planting", planting.id, season_year))
        if direct is not None:
            value = getattr(direct, metric_code)
            if value is not None:
                metric_value = float(value)
                return {
                    "value": metric_value,
                    "value_per_hectare": self._per_hectare(metric_value, planting_area),
                    "source_scope": "planting",
                    "source_mix": {"planting": 1},
                    "sample_tree_count": None,
                    "survey_count": None,
                }

        section_values = []
        for section in active_sections:
            section_stats = stats_by_scope.get(("section", section.id, season_year))
            if section_stats is None:
                continue
            value = getattr(section_stats, metric_code)
            if value is not None:
                section_values.append(float(value))
        if section_values:
            metric_value = sum(section_values)
            return {
                "value": metric_value,
                "value_per_hectare": self._per_hectare(metric_value, planting_area),
                "source_scope": "section",
                "source_mix": {"section": len(section_values), "missing": len(active_sections) - len(section_values)},
                "sample_tree_count": None,
                "survey_count": None,
            }

        field_stats = stats_by_scope.get(("field", field.id, season_year))
        if field_stats is not None:
            value = getattr(field_stats, metric_code)
            field_area = self._field_area_for_year(field, season_year)
            if value is not None and field_area > 0:
                metric_value = float(value) * (planting_area / field_area)
                return {
                    "value": metric_value,
                    "value_per_hectare": self._per_hectare(metric_value, planting_area),
                    "source_scope": "field",
                    "source_mix": {"field": 1},
                    "sample_tree_count": None,
                    "survey_count": None,
                }

        return self._missing_yearly_metric(len(active_sections))

    def _per_hectare(self, value: float | None, area_square_metres: float | None) -> float | None:
        if value is None or area_square_metres is None or area_square_metres <= 0:
            return None
        return value / (area_square_metres / 10000)

    def _metric_for_year(
        self,
        *,
        metric_definition: dict[str, Any],
        field: models.Field,
        planting: models.Planting,
        season_year: int,
        surveys_by_scope: dict[tuple[str, int, int, str], list[models.FruitCountSurvey]],
        stats_by_scope: dict[tuple[str, int, int], models.YearlyStats],
    ) -> dict[str, Any]:
        metric_code = metric_definition["metric_code"]
        if metric_code.startswith(COUNT_METRIC_PREFIX):
            return self._planting_count_metric_for_timing_codes(
                field=field,
                planting=planting,
                season_year=season_year,
                timing_codes=metric_definition["timing_codes"],
                surveys_by_scope=surveys_by_scope,
            )
        return self._planting_yearly_metric(
            field=field,
            planting=planting,
            season_year=season_year,
            metric_code=metric_code,
            stats_by_scope=stats_by_scope,
        )

    def _summary_metric(
        self,
        *,
        metric_code: str,
        rows: list[dict[str, Any]],
        season_year: int,
    ) -> dict[str, Any]:
        metric_values = [
            (
                row["history_by_year"][season_year]["metrics"][metric_code]["value"],
                row["tree_count_by_year"][season_year]
                if row["tree_count_by_year"][season_year] is not None
                else row["area_by_year"][season_year],
            )
            for row in rows
            if row["history_by_year"][season_year]["metrics"][metric_code]["value"] is not None
            and row["active_by_year"][season_year]
        ]

        if metric_code.startswith(COUNT_METRIC_PREFIX):
            value = self._weighted_mean(metric_values)
            return {
                "value": value,
                "value_per_hectare": None,
                "source_scope": "summary",
                "source_mix": {},
                "sample_tree_count": sum(
                    row["history_by_year"][season_year]["metrics"][metric_code]["sample_tree_count"] or 0
                    for row in rows
                    if row["active_by_year"][season_year]
                ),
                "survey_count": sum(
                    row["history_by_year"][season_year]["metrics"][metric_code]["survey_count"] or 0
                    for row in rows
                    if row["active_by_year"][season_year]
                ),
            }

        value = sum(value for value, _ in metric_values) if metric_values else None
        area = sum(row["area_by_year"][season_year] for row in rows if row["active_by_year"][season_year])
        return {
            "value": value,
            "value_per_hectare": self._per_hectare(value, area),
            "source_scope": "summary",
            "source_mix": {},
            "sample_tree_count": None,
            "survey_count": None,
        }

    def _build_summary(
        self,
        *,
        rows: list[dict[str, Any]],
        years: list[int],
        selected_year: int,
    ) -> dict[str, Any]:
        area = sum(
            row["area_by_year"][selected_year]
            for row in rows
            if row["active_by_year"][selected_year]
        )
        tree_counts = [
            row["tree_count_by_year"][selected_year]
            for row in rows
            if row["active_by_year"][selected_year] and row["tree_count_by_year"][selected_year] is not None
        ]
        summary_history = []
        history_by_year = {}
        for year in years:
            history_entry = {
                "season_year": year,
                "metrics": {
                    metric["metric_code"]: self._summary_metric(
                        metric_code=metric["metric_code"],
                        rows=rows,
                        season_year=year,
                    )
                    for metric in FIELD_STATISTICS_METRICS
                },
            }
            summary_history.append(history_entry)
            history_by_year[year] = history_entry
        return {
            "label": "Summe",
            "area": area,
            "area_ha": area / 10000,
            "section_count": sum(
                row["section_count_by_year"][selected_year]
                for row in rows
                if row["active_by_year"][selected_year]
            ),
            "tree_count": sum(tree_counts) if tree_counts else None,
            "metrics": history_by_year[selected_year]["metrics"] if selected_year in history_by_year else {},
            "history": summary_history,
        }

    def _filter_fields(
        self,
        *,
        fields: list[models.Field],
        field_ids: list[int] | None,
    ) -> list[models.Field]:
        if field_ids is None:
            return fields
        requested_ids = {int(field_id) for field_id in field_ids}
        filtered_fields = [field for field in fields if field.id in requested_ids]
        missing_ids = requested_ids - {field.id for field in filtered_fields}
        if missing_ids:
            raise ValueError(f"Unknown field ids: {sorted(missing_ids)}")
        return filtered_fields

    def get_field_statistics(
        self,
        *,
        season_year: int | None = None,
        field_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        available_years: set[int] = set()

        with self.db.session_scope() as session:
            fields = self._filter_fields(
                fields=self.db.fields.list_all(session),
                field_ids=field_ids,
            )

            field_data = []
            for field in fields:
                surveys = self.db.fruit_counts.list_for_field(
                    session,
                    field_id=field.id,
                    include_excluded=False,
                )
                stats = self.db.yearly_stats.list_for_field(session, field_id=field.id)
                available_years.update(survey.season_year for survey in surveys)
                available_years.update(item.season_year for item in stats)
                field_data.append(
                    (
                        field,
                        self._index_count_surveys(surveys)[0],
                        self._index_yearly_stats(stats),
                    )
                )

            sorted_years = sorted(available_years)
            selected_year = int(season_year) if season_year is not None else (sorted_years[-1] if sorted_years else 0)
            if season_year is not None:
                available_years.add(selected_year)
                sorted_years = sorted(available_years)
            years = sorted_years or ([selected_year] if selected_year else [])

            for field, surveys_by_scope, stats_by_scope in field_data:
                for planting in field.plantings:
                    history = []
                    history_by_year = {}
                    active_by_year = {}
                    area_by_year = {}
                    tree_count_by_year = {}
                    section_count_by_year = {}
                    for year in years:
                        active_sections = self._planting_sections_for_year(planting, year)
                        is_active = planting_active_in_year(planting, year)
                        active_by_year[year] = is_active
                        area_by_year[year] = self._planting_area_for_year(planting, year)
                        tree_count_by_year[year] = self._planting_tree_count_for_year(planting, year)
                        section_count_by_year[year] = len(active_sections)
                        metrics = {
                            metric["metric_code"]: self._metric_for_year(
                                metric_definition=metric,
                                field=field,
                                planting=planting,
                                season_year=year,
                                surveys_by_scope=surveys_by_scope,
                                stats_by_scope=stats_by_scope,
                            )
                            for metric in FIELD_STATISTICS_METRICS
                        }
                        history_entry = {
                            "season_year": year,
                            "metrics": metrics,
                        }
                        history.append(history_entry)
                        history_by_year[year] = history_entry

                    if not active_by_year.get(selected_year, False):
                        continue

                    selected_metrics = history_by_year.get(selected_year, {"metrics": {}})["metrics"]
                    area = area_by_year.get(selected_year, 0)
                    rows.append(
                        {
                            "field_id": field.id,
                            "field_group": field.group,
                            "field_name": field.name,
                            "planting_id": planting.id,
                            "planting_name": planting.variety.name,
                            "active": active_by_year.get(selected_year, False),
                            "section_count": section_count_by_year.get(selected_year, 0),
                            "area": area,
                            "area_ha": area / 10000,
                            "tree_count": tree_count_by_year.get(selected_year),
                            "metrics": selected_metrics,
                            "history": history,
                            "history_by_year": history_by_year,
                            "active_by_year": active_by_year,
                            "area_by_year": area_by_year,
                            "tree_count_by_year": tree_count_by_year,
                            "section_count_by_year": section_count_by_year,
                        }
                    )

        response_rows = [
            {
                key: value
                for key, value in row.items()
                if key not in {
                    "history_by_year",
                    "active_by_year",
                    "area_by_year",
                    "tree_count_by_year",
                    "section_count_by_year",
                }
            }
            for row in rows
        ]
        summary = self._build_summary(rows=rows, years=years, selected_year=selected_year)

        return {
            "season_year": selected_year,
            "available_years": sorted(available_years, reverse=True),
            "history_years": years,
            "metrics": list(FIELD_STATISTICS_METRICS),
            "rows": response_rows,
            "summary": summary,
        }
