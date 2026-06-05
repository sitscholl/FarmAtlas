import datetime
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ...metrics import MetricAccumulatorService
from .. import models
from ..core import DatabaseCore
from ..repositories import CropProtectionRepository, FieldWeatherRepository


VALID_METRIC_TYPES = {"days_since", "rain_since", "gdd_since"}


@dataclass(frozen=True)
class CropProtectionMetricEvaluation:
    metric_type: str
    value: float | int | None
    threshold: float
    warning_threshold: float | None
    status: str


@dataclass(frozen=True)
class CropProtectionRuleEvaluation:
    rule_id: int
    rule_name: str
    section_id: int
    section_name: str
    field_id: int
    field_name: str
    status: str
    last_treatment_date: datetime.date | None
    last_treatment_product: str | None
    metrics: list[CropProtectionMetricEvaluation]


class CropProtectionService:
    def __init__(
        self,
        core: DatabaseCore,
        crop_protection: CropProtectionRepository,
        field_weather: FieldWeatherRepository,
    ) -> None:
        self._core = core
        self._crop_protection = crop_protection
        self._field_weather = field_weather

    def _validate_rule_payload(
        self,
        *,
        name: str,
        logic: str,
        product_names: list[str],
        scopes: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
        **_: Any,
    ) -> None:
        if not name.strip():
            raise ValueError("name must not be empty")
        if logic.strip().lower() not in {"any", "all"}:
            raise ValueError("logic must be either 'any' or 'all'")
        if not [product for product in product_names if product.strip()]:
            raise ValueError("At least one product_name is required")
        if not scopes:
            raise ValueError("At least one rule scope is required")
        enabled_metrics = [metric for metric in metrics if metric.get("enabled", True)]
        if not enabled_metrics:
            raise ValueError("At least one enabled metric is required")
        for metric in metrics:
            metric_type = str(metric["metric_type"]).strip().lower()
            if metric_type not in VALID_METRIC_TYPES:
                raise ValueError(f"Invalid metric_type {metric_type!r}")
            if float(metric["threshold"]) <= 0:
                raise ValueError("metric threshold must be greater than 0")
            warning_threshold = metric.get("warning_threshold")
            if warning_threshold is not None and float(warning_threshold) < 0:
                raise ValueError("metric warning_threshold must be greater than or equal to 0")

    def create_rule(self, **payload) -> models.CropProtectionRule:
        self._validate_rule_payload(**payload)
        with self._core.session_scope() as session:
            return self._crop_protection.create(session, **payload)

    def update_rule(self, rule_id: int, **payload) -> models.CropProtectionRule:
        self._validate_rule_payload(**payload)
        with self._core.session_scope() as session:
            return self._crop_protection.update(session, rule_id, **payload)

    def delete_rule(self, rule_id: int) -> bool:
        with self._core.session_scope() as session:
            return self._crop_protection.delete(session, rule_id)

    def _season_bounds(
        self,
        rule: models.CropProtectionRule,
        *,
        season_year: int,
        as_of: datetime.date,
    ) -> tuple[datetime.date, datetime.date]:
        start = rule.season_start or datetime.date(season_year, 1, 1)
        end = rule.season_end or datetime.date(season_year, 12, 31)
        return start, min(end, as_of)

    def _weather_dataframe(
        self,
        session,
        *,
        field_id: int,
        start: datetime.date,
        end: datetime.date,
    ) -> pd.DataFrame:
        rows = self._field_weather.list_for_field(
            session,
            field_id=field_id,
            start=start,
            end=end + datetime.timedelta(days=1),
        )
        return pd.DataFrame(
            [
                {
                    "date": row.date,
                    "precipitation": row.precipitation,
                    "tmin": row.tmin,
                    "tmax": row.tmax,
                    "tmean": row.tmean,
                }
                for row in rows
            ]
        )

    def _evaluate_metric(
        self,
        metric: models.CropProtectionRuleMetric,
        accumulator: MetricAccumulatorService,
        *,
        start_date: datetime.date,
        as_of: datetime.date,
    ) -> CropProtectionMetricEvaluation:
        metric_type = metric.metric_type
        value: float | int | None
        if metric_type == "days_since":
            value = accumulator.days_since(start_date, as_of)
        elif metric_type == "rain_since":
            if accumulator.daily_weather.empty:
                value = None
            else:
                value = accumulator.precipitation_since(start_date, as_of)
        elif metric_type == "gdd_since":
            if accumulator.daily_weather.empty:
                value = None
            else:
                base_temperature = float((metric.metric_config or {}).get("base_temperature", 10.0))
                value = accumulator.gdd_since(start_date, as_of, base_temperature=base_temperature)
        else:
            raise ValueError(f"Unsupported metric_type {metric_type!r}")

        if value is None:
            status = "missing"
        elif value >= metric.threshold:
            status = "due"
        elif metric.warning_threshold is not None and value >= metric.warning_threshold:
            status = "soon"
        else:
            status = "ok"

        return CropProtectionMetricEvaluation(
            metric_type=metric_type,
            value=value,
            threshold=float(metric.threshold),
            warning_threshold=None if metric.warning_threshold is None else float(metric.warning_threshold),
            status=status,
        )

    def _combine_metric_statuses(self, rule: models.CropProtectionRule, metric_statuses: list[str]) -> str:
        if not metric_statuses:
            return "missing"

        if rule.logic == "all":
            if all(status == "due" for status in metric_statuses):
                return "due"
            if all(status in {"due", "soon"} for status in metric_statuses):
                return "soon"
            if any(status == "missing" for status in metric_statuses):
                return "missing"
            return "ok"

        if any(status == "due" for status in metric_statuses):
            return "due"
        if any(status == "soon" for status in metric_statuses):
            return "soon"
        if any(status == "missing" for status in metric_statuses):
            return "missing"
        return "ok"

    def evaluate_rules(
        self,
        *,
        rule_id: int | None = None,
        season_year: int | None = None,
        as_of: datetime.date | None = None,
        include_disabled: bool = False,
    ) -> list[CropProtectionRuleEvaluation]:
        as_of = as_of or datetime.date.today()
        season_year = season_year or as_of.year

        with self._core.session_scope() as session:
            if rule_id is None:
                rules = self._crop_protection.list_rules(
                    session,
                    enabled=None if include_disabled else True,
                )
            else:
                rule = self._crop_protection.get_by_id(session, rule_id)
                if rule is None:
                    raise ValueError(f"Could not find any crop protection rule with id {rule_id}")
                rules = [rule] if include_disabled or rule.enabled else []

            evaluations: list[CropProtectionRuleEvaluation] = []
            for rule in rules:
                section_ids = self._crop_protection.expand_rule_section_ids(session, rule)
                sections_by_id = self._crop_protection.get_section_contexts(session, section_ids)
                product_names = [product.product_name for product in rule.products]
                enabled_metrics = [metric for metric in rule.metrics if metric.enabled]
                season_start, season_end = self._season_bounds(rule, season_year=season_year, as_of=as_of)

                for section_id in section_ids:
                    section = sections_by_id.get(section_id)
                    if section is None or section.field is None:
                        continue

                    last_treatment = self._crop_protection.latest_matching_treatment(
                        session,
                        section_id=section_id,
                        product_names=product_names,
                        start=season_start,
                        end=season_end,
                    )
                    if last_treatment is None:
                        evaluations.append(
                            CropProtectionRuleEvaluation(
                                rule_id=rule.id,
                                rule_name=rule.name,
                                section_id=section.id,
                                section_name=section.name,
                                field_id=section.field.id,
                                field_name=section.field.name,
                                status="missing",
                                last_treatment_date=None,
                                last_treatment_product=None,
                                metrics=[],
                            )
                        )
                        continue

                    weather = self._weather_dataframe(
                        session,
                        field_id=section.field.id,
                        start=last_treatment.date,
                        end=as_of,
                    )
                    accumulator = MetricAccumulatorService(weather)
                    metric_evaluations = [
                        self._evaluate_metric(
                            metric,
                            accumulator,
                            start_date=last_treatment.date,
                            as_of=as_of,
                        )
                        for metric in enabled_metrics
                    ]
                    status = self._combine_metric_statuses(
                        rule,
                        [metric.status for metric in metric_evaluations],
                    )
                    evaluations.append(
                        CropProtectionRuleEvaluation(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            section_id=section.id,
                            section_name=section.name,
                            field_id=section.field.id,
                            field_name=section.field.name,
                            status=status,
                            last_treatment_date=last_treatment.date,
                            last_treatment_product=last_treatment.product_name,
                            metrics=metric_evaluations,
                        )
                    )

            return evaluations
