import datetime
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ...domain.field import FieldContext
from ...metrics import MetricAccumulatorService
from ...weather_frame import WeatherFrame
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
    weather_updated_at: datetime.datetime | None
    metrics: list[CropProtectionMetricEvaluation]


@dataclass(frozen=True)
class _CropProtectionEvaluationCase:
    order: int
    rule: models.CropProtectionRule
    section: models.Section
    last_treatment: models.TreatmentEvent
    enabled_metrics: list[models.CropProtectionRuleMetric]


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
        self._weather_cache_service: Any | None = None

    def set_weather_cache_service(self, weather_cache_service: Any) -> None:
        self._weather_cache_service = weather_cache_service

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

    def _weather_frame(
        self,
        session,
        *,
        field: models.Field,
        start: datetime.date | datetime.datetime,
        end: datetime.date | datetime.datetime,
    ) -> WeatherFrame:
        if self._weather_cache_service is not None:
            return self._weather_cache_service.get_field_hourly_weather(
                FieldContext.from_model(field),
                start=start,
                end=end,
                ensure=False,
            )

        rows = self._field_weather.list_station_hourly(
            session,
            provider=field.reference_provider,
            station=field.reference_station,
            start=start,
            end=end,
        )
        frame = pd.DataFrame(
            [
                {
                    "timestamp": row.timestamp,
                    "precipitation": row.precipitation,
                    "tair_2m": row.tair_2m,
                    "relative_humidity": row.relative_humidity,
                    "wind_speed": row.wind_speed,
                    "wind_gust": row.wind_gust,
                    "air_pressure": row.air_pressure,
                    "sun_duration": row.sun_duration,
                    "solar_radiation": row.solar_radiation,
                    "et0": row.et0,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]
        )
        return WeatherFrame(
            data=frame,
            resolution="1h",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            source_provider=field.reference_provider,
            source_station=field.reference_station,
        )

    def _resolve_as_of(
        self,
        as_of: datetime.date | datetime.datetime | None,
    ) -> datetime.date | datetime.datetime:
        if as_of is not None:
            return as_of
        if self._weather_cache_service is not None:
            return pd.Timestamp.now(tz=self._weather_cache_service.timezone).floor("h").to_pydatetime()
        return datetime.datetime.now().replace(minute=0, second=0, microsecond=0)

    def _weather_window_end(
        self,
        as_of: datetime.date | datetime.datetime,
    ) -> datetime.date | datetime.datetime:
        if isinstance(as_of, datetime.datetime):
            return as_of + datetime.timedelta(hours=1)
        return as_of + datetime.timedelta(days=1)

    def _evaluate_metric(
        self,
        metric: models.CropProtectionRuleMetric,
        accumulator: MetricAccumulatorService,
        *,
        start_date: datetime.date,
        as_of: datetime.date | datetime.datetime,
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

    def _metrics_require_weather(self, metrics: list[models.CropProtectionRuleMetric]) -> bool:
        return any(metric.metric_type in {"rain_since", "gdd_since"} for metric in metrics)

    def _empty_weather_frame(
        self,
        field: models.Field,
        *,
        start: datetime.date | datetime.datetime,
        end: datetime.date | datetime.datetime,
    ) -> WeatherFrame:
        return WeatherFrame(
            data=pd.DataFrame(),
            resolution="1h",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            source_provider=field.reference_provider,
            source_station=field.reference_station,
        )

    def _weather_frames_for_cases(
        self,
        session,
        cases: list[_CropProtectionEvaluationCase],
        *,
        end: datetime.date | datetime.datetime,
    ) -> dict[int, WeatherFrame]:
        weather_cases = [
            case
            for case in cases
            if self._metrics_require_weather(case.enabled_metrics)
        ]
        if not weather_cases:
            return {}

        field_contexts_by_id: dict[int, FieldContext] = {}
        fields_by_id: dict[int, models.Field] = {}
        start_by_field_id: dict[int, datetime.date] = {}
        for case in weather_cases:
            field = case.section.field
            fields_by_id[field.id] = field
            current_start = start_by_field_id.get(field.id)
            if current_start is None or case.last_treatment.date < current_start:
                start_by_field_id[field.id] = case.last_treatment.date
            if self._weather_cache_service is not None:
                field_contexts_by_id[field.id] = FieldContext.from_model(field)

        if self._weather_cache_service is not None:
            return {
                field_id: self._weather_cache_service.get_field_hourly_weather(
                    field_context,
                    start=start_by_field_id[field_id],
                    end=end,
                    ensure=False,
                )
                for field_id, field_context in field_contexts_by_id.items()
            }

        return {
            field_id: self._weather_frame(
                session,
                field=fields_by_id[field_id],
                start=start,
                end=end,
            )
            for field_id, start in start_by_field_id.items()
        }

    def evaluate_rules(
        self,
        *,
        rule_id: int | None = None,
        season_year: int | None = None,
        as_of: datetime.date | datetime.datetime | None = None,
        include_disabled: bool = False,
    ) -> list[CropProtectionRuleEvaluation]:
        as_of = self._resolve_as_of(as_of)
        as_of_date = as_of.date() if isinstance(as_of, datetime.datetime) else as_of
        weather_end = self._weather_window_end(as_of)
        season_year = season_year or as_of_date.year

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

            ordered_evaluations: list[tuple[int, CropProtectionRuleEvaluation]] = []
            all_evaluation_cases: list[_CropProtectionEvaluationCase] = []
            next_order = 0
            for rule in rules:
                section_ids = self._crop_protection.expand_rule_section_ids(session, rule)
                sections_by_id = self._crop_protection.get_section_contexts(session, section_ids)
                product_names = [product.product_name for product in rule.products]
                enabled_metrics = [metric for metric in rule.metrics if metric.enabled]
                season_start, season_end = self._season_bounds(rule, season_year=season_year, as_of=as_of_date)
                rule_evaluation_cases: list[tuple[models.Section, models.TreatmentEvent]] = []

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
                        ordered_evaluations.append(
                            (
                                next_order,
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
                                    weather_updated_at=None,
                                    metrics=[],
                                ),
                            )
                        )
                        next_order += 1
                        continue

                    rule_evaluation_cases.append((section, last_treatment))

                for section, last_treatment in rule_evaluation_cases:
                    all_evaluation_cases.append(
                        _CropProtectionEvaluationCase(
                            order=next_order,
                            rule=rule,
                            section=section,
                            last_treatment=last_treatment,
                            enabled_metrics=enabled_metrics,
                        )
                    )
                    next_order += 1

            weather_by_field_id = self._weather_frames_for_cases(
                session,
                all_evaluation_cases,
                end=weather_end,
            )

            for case in all_evaluation_cases:
                section = case.section
                last_treatment = case.last_treatment
                weather = weather_by_field_id.get(section.field.id)
                if weather is None:
                    if self._metrics_require_weather(case.enabled_metrics):
                        weather = self._weather_frame(
                            session,
                            field=section.field,
                            start=last_treatment.date,
                            end=weather_end,
                        )
                    else:
                        weather = self._empty_weather_frame(
                            section.field,
                            start=last_treatment.date,
                            end=weather_end,
                        )
                accumulator = MetricAccumulatorService(weather)
                metric_evaluations = [
                    self._evaluate_metric(
                        metric,
                        accumulator,
                        start_date=last_treatment.date,
                        as_of=as_of,
                    )
                    for metric in case.enabled_metrics
                ]
                status = self._combine_metric_statuses(
                    case.rule,
                    [metric.status for metric in metric_evaluations],
                )
                weather_updated_at = weather.updated_at
                ordered_evaluations.append(
                    (
                        case.order,
                        CropProtectionRuleEvaluation(
                            rule_id=case.rule.id,
                            rule_name=case.rule.name,
                            section_id=section.id,
                            section_name=section.name,
                            field_id=section.field.id,
                            field_name=section.field.name,
                            status=status,
                            last_treatment_date=last_treatment.date,
                            last_treatment_product=last_treatment.product_name,
                            weather_updated_at=weather_updated_at,
                            metrics=metric_evaluations,
                        ),
                    )
                )

            return [
                evaluation
                for _, evaluation in sorted(ordered_evaluations, key=lambda item: item[0])
            ]
