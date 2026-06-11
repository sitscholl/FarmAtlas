from __future__ import annotations

import datetime
from dataclasses import dataclass, field
import logging
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import pandas as pd

from ..field import FieldContext
from ..field_weather import FieldWeatherCacheService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WeatherRefreshStationResult:
    workflow_name: str
    source_provider: str
    source_station: str
    cache_kind: str
    status: str
    start: datetime.datetime
    end: datetime.datetime
    field_ids: list[int]
    row_count: int = 0
    refreshed: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status != "failed"


@dataclass(slots=True)
class WeatherRefreshResult:
    workflow_name: str
    status: str
    station_count: int
    field_count: int
    start: datetime.datetime
    end: datetime.datetime
    station_results: list[WeatherRefreshStationResult] = field(default_factory=list)
    cleaned_row_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status != "failed"


@dataclass
class WeatherRefreshWorkflow:
    workflow_name: ClassVar[str] = "refresh_weather_cache"
    requires_fields: ClassVar[bool] = True

    cache_service: FieldWeatherCacheService
    timezone: ZoneInfo

    @property
    def name(self) -> str:
        return self.workflow_name

    def _resolve_window(
        self,
        *,
        start: datetime.datetime | datetime.date | str | None = None,
        end: datetime.datetime | datetime.date | str | None = None,
        lookback_days: int = 180,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        end_ts = (
            pd.Timestamp.now(tz=self.timezone).ceil("h")
            if end is None
            else self.cache_service._to_timestamp(end).ceil("h")
        )
        start_ts = (
            end_ts - pd.Timedelta(days=int(lookback_days))
            if start is None
            else self.cache_service._to_timestamp(start).floor("h")
        )
        if start_ts >= end_ts:
            raise ValueError("Weather cache refresh start must be before end")
        return start_ts, end_ts

    def _station_groups(
        self,
        fields: list[FieldContext],
        *,
        active_only: bool,
    ) -> dict[tuple[str, str], list[FieldContext]]:
        groups: dict[tuple[str, str], list[FieldContext]] = {}
        for fld in fields:
            if active_only and not fld.active:
                continue
            groups.setdefault((fld.reference_provider, fld.reference_station), []).append(fld)
        return groups

    def run(
        self,
        fields: list[FieldContext],
        *,
        start: datetime.datetime | datetime.date | str | None = None,
        end: datetime.datetime | datetime.date | str | None = None,
        lookback_days: int = 180,
        max_age_hours: float = 0,
        force: bool = False,
        active_only: bool = True,
        refresh_forecast: bool = True,
        forecast_provider: str = "open-meteo",
        forecast_days: int = 7,
        cleanup_older_than_days: int | None = None,
    ) -> WeatherRefreshResult:
        start_ts, end_ts = self._resolve_window(
            start=start,
            end=end,
            lookback_days=lookback_days,
        )
        max_age = datetime.timedelta(hours=float(max_age_hours))
        station_groups = self._station_groups(fields, active_only=active_only)
        station_results: list[WeatherRefreshStationResult] = []

        for (provider, station), station_fields in station_groups.items():
            try:
                weather = self.cache_service.ensure_station_hourly_weather(
                    provider=provider,
                    station=station,
                    start=start_ts,
                    end=end_ts,
                    max_age=max_age,
                    force=force,
                )
                station_results.append(
                    WeatherRefreshStationResult(
                        workflow_name=self.name,
                        source_provider=provider,
                        source_station=station,
                        cache_kind="observed",
                        status="success",
                        start=start_ts.to_pydatetime(),
                        end=end_ts.to_pydatetime(),
                        field_ids=sorted(field.id for field in station_fields),
                        row_count=int(len(weather.data.index)),
                        refreshed=weather.refreshed,
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Refreshing weather cache failed for station %s/%s",
                    provider,
                    station,
                )
                station_results.append(
                    WeatherRefreshStationResult(
                        workflow_name=self.name,
                        source_provider=provider,
                        source_station=station,
                        cache_kind="observed",
                        status="failed",
                        start=start_ts.to_pydatetime(),
                        end=end_ts.to_pydatetime(),
                        field_ids=sorted(field.id for field in station_fields),
                        error=str(exc),
                    )
                )

            if not refresh_forecast or int(forecast_days) <= 0:
                continue

            forecast_start = end_ts.floor("h")
            forecast_end = forecast_start + pd.Timedelta(days=int(forecast_days))
            try:
                forecast_result = self.cache_service.refresh_station_hourly(
                    provider=forecast_provider,
                    station=station,
                    start=forecast_start,
                    end=forecast_end,
                    value_type="forecast",
                )
                stale_before_count = self.cache_service.clear_station_hourly_cache(
                    provider=forecast_provider,
                    station=station,
                    end=forecast_start,
                    value_type="forecast",
                )
                stale_after_count = self.cache_service.clear_station_hourly_cache(
                    provider=forecast_provider,
                    station=station,
                    start=forecast_end,
                    value_type="forecast",
                )
                station_results.append(
                    WeatherRefreshStationResult(
                        workflow_name=self.name,
                        source_provider=forecast_provider,
                        source_station=station,
                        cache_kind="forecast",
                        status="success",
                        start=forecast_start.to_pydatetime(),
                        end=forecast_end.to_pydatetime(),
                        field_ids=sorted(field.id for field in station_fields),
                        row_count=forecast_result.upserted_count,
                        refreshed=True,
                        metadata={
                            "stale_before_count": stale_before_count,
                            "stale_after_count": stale_after_count,
                        },
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Refreshing weather forecast cache failed for station %s/%s",
                    forecast_provider,
                    station,
                )
                station_results.append(
                    WeatherRefreshStationResult(
                        workflow_name=self.name,
                        source_provider=forecast_provider,
                        source_station=station,
                        cache_kind="forecast",
                        status="failed",
                        start=forecast_start.to_pydatetime(),
                        end=forecast_end.to_pydatetime(),
                        field_ids=sorted(field.id for field in station_fields),
                        error=str(exc),
                    )
                )

        cleaned_row_count = 0
        if cleanup_older_than_days is not None:
            cleaned_row_count = self.cache_service.cleanup_station_hourly_cache(
                older_than=datetime.timedelta(days=int(cleanup_older_than_days)),
                now=end_ts,
            )

        failed_count = sum(1 for result in station_results if not result.ok)
        status = "success"
        if failed_count == len(station_results) and station_results:
            status = "failed"
        elif failed_count:
            status = "warning"

        return WeatherRefreshResult(
            workflow_name=self.name,
            status=status,
            station_count=len(station_groups),
            field_count=sum(len(station_fields) for station_fields in station_groups.values()),
            start=start_ts.to_pydatetime(),
            end=end_ts.to_pydatetime(),
            station_results=station_results,
            cleaned_row_count=cleaned_row_count,
            metadata={
                "active_only": active_only,
                "force": force,
                "lookback_days": int(lookback_days),
                "max_age_hours": float(max_age_hours),
                "refresh_forecast": refresh_forecast,
                "forecast_provider": forecast_provider,
                "forecast_days": int(forecast_days),
                "cleanup_older_than_days": cleanup_older_than_days,
            },
        )
