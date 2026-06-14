from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from .types import ApplicationFieldResult
from ..calculation.soil_water import estimate_available_water_storage_capacity
from ..calculation.water_balance import calculate_water_balance
from ..database.db import Database
from ..et.et_correction import ETCorrection
from ..domain.field import FieldContext
from ..domain.irrigation import FieldIrrigation
from ..field_weather import FieldWeatherCacheService
from ..results import FarmAtlasError, FarmAtlasWarning
from ..weather_frame import WeatherFrame

logger = logging.getLogger(__name__)


def missing_soil_parameters(field: FieldContext) -> list[str]:
    missing: list[str] = []
    if field.soil_type is None:
        missing.append("soil_type")
    if field.humus_pct is None:
        missing.append("humus_pct")
    if field.effective_root_depth_cm is None:
        missing.append("effective_root_depth_cm")
    if field.p_allowable is None:
        missing.append("p_allowable")
    return missing


@dataclass(slots=True)
class WaterBalanceSummary:
    field_id: int
    as_of: date | None
    current_water_deficit: float | None
    current_soil_water_content: float | None
    available_water_storage: float | None
    readily_available_water: float | None
    below_raw: bool | None
    safe_ratio: float | None


@dataclass
class WaterBalanceService:
    db: Database
    weather_cache: FieldWeatherCacheService
    et_corrector: ETCorrection
    timezone: ZoneInfo
    forecast_provider: str = "open-meteo"

    operation_name: str = "water_balance"

    def _empty_summary(self, field_id: int) -> WaterBalanceSummary:
        return WaterBalanceSummary(
            field_id=field_id,
            as_of=None,
            current_water_deficit=None,
            current_soil_water_content=None,
            available_water_storage=None,
            readily_available_water=None,
            below_raw=None,
            safe_ratio=None,
        )

    def _field_result(
        self,
        field: FieldContext,
        *,
        result: pd.DataFrame | None = None,
        warnings: list[FarmAtlasWarning] | FarmAtlasWarning | None = None,
        errors: list[FarmAtlasError] | FarmAtlasError | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApplicationFieldResult[pd.DataFrame]:
        return ApplicationFieldResult(
            operation_name=self.operation_name,
            field_id=field.id,
            field_name=field.name,
            result=result,
            warnings=warnings,
            errors=errors,
            status=status,
            metadata=metadata or {},
        )

    def _period_end(
        self,
        *,
        forecast_days: int = 0,
        as_of: pd.Timestamp | None = None,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        observe_end = (
            pd.Timestamp.now(tz=self.timezone).floor("D")
            if as_of is None
            else self.weather_cache._to_timestamp(as_of).floor("D")
        )
        period_end = observe_end + pd.Timedelta(days=max(int(forecast_days), 0))
        return observe_end, period_end

    def _daily_weather(
        self,
        field: FieldContext,
        *,
        start: pd.Timestamp,
        observe_end: pd.Timestamp,
        period_end: pd.Timestamp,
    ) -> pd.DataFrame:
        hourly_frames: list[pd.DataFrame] = []

        if start < observe_end:
            observed = self.weather_cache.get_field_hourly_weather(
                field,
                start=start,
                end=observe_end,
                ensure=False,
            )
            if not observed.empty:
                hourly_frames.append(observed.data)

        if period_end > observe_end:
            forecast = self.weather_cache.get_station_hourly_weather(
                provider=self.forecast_provider,
                station=field.reference_station,
                start=observe_end,
                end=period_end,
            )
            if not forecast.empty:
                hourly_frames.append(forecast.data)

        if not hourly_frames:
            return pd.DataFrame()

        hourly = pd.concat(hourly_frames).sort_index()
        hourly = hourly.loc[(hourly.index >= start) & (hourly.index < period_end)]
        if hourly.empty:
            return pd.DataFrame()

        daily = self.weather_cache.aggregate_daily(
            WeatherFrame(
                data=hourly,
                resolution="1h",
                start=start,
                end=period_end,
                source_provider=field.reference_provider,
                source_station=field.reference_station,
            )
        ).data
        if daily.empty:
            return daily

        datetime_column = "datetime" if "datetime" in daily.columns else "timestamp" if "timestamp" in daily.columns else None
        if datetime_column is not None:
            daily[datetime_column] = pd.to_datetime(daily[datetime_column])
            daily = daily.set_index(datetime_column)
        elif not isinstance(daily.index, pd.DatetimeIndex):
            raise TypeError("Daily cached weather must contain a datetime or timestamp column.")
        return daily.sort_index()

    def _prepare_daily_weather_for_field(
        self,
        field: FieldContext,
        daily_weather: pd.DataFrame,
    ) -> pd.DataFrame:
        prepared = daily_weather.copy()
        if "et0" in prepared.columns and prepared["et0"].notna().any():
            prepared = self.et_corrector.apply_to_field(prepared, "et0", field)
            if prepared["et0_corrected"].isna().any():
                raise KeyError("Cached weather has gaps in et0 values.")
            return prepared

        if "et0_corrected" in prepared.columns and prepared["et0_corrected"].notna().any():
            prepared["kc"] = self.et_corrector.to_field_series(prepared.index, field)
            if prepared["et0_corrected"].isna().any():
                raise KeyError("Cached weather has gaps in et0_corrected values.")
            return prepared

        raise KeyError("Cached weather does not contain complete et0 or et0_corrected values.")

    def calculate_field(
        self,
        field: FieldContext,
        *,
        year: int | None = None,
        forecast_days: int = 0,
    ) -> ApplicationFieldResult[pd.DataFrame]:
        year = year or pd.Timestamp.now(tz=self.timezone).year
        observe_end, period_end = self._period_end(forecast_days=forecast_days)

        try:
            missing_parameters = missing_soil_parameters(field)
            if missing_parameters:
                return self._field_result(
                    field,
                    warnings=FarmAtlasWarning(
                        message=(
                            f"Field {field.name} is missing required soil parameters: "
                            f"{', '.join(missing_parameters)}."
                        ),
                        code="MISSING_SOIL_PARAMETERS",
                        details={"missing_parameters": missing_parameters},
                    ),
                    status="skipped",
                    metadata={"source": "computed_from_weather_cache"},
                )

            with self.db.session_scope() as session:
                first_irrigation = self.db.irrigation.get_first_for_year(session, field_id=field.id, year=year)
                if first_irrigation is None:
                    return self._field_result(
                        field,
                        warnings=FarmAtlasWarning(
                            message=f"No irrigation events found for field {field.name} in {year}.",
                            code="NO_IRRIGATION",
                            details={"year": year},
                        ),
                        status="skipped",
                        metadata={"source": "computed_from_weather_cache"},
                    )
                irrigation_events = self.db.irrigation.list(
                    session,
                    field_id=field.id,
                    start=pd.Timestamp(year=year, month=1, day=1).date(),
                    end=period_end.date(),
                )

            start = pd.Timestamp(first_irrigation.date, tz=self.timezone)
            daily_weather = self._daily_weather(
                field,
                start=start,
                observe_end=observe_end,
                period_end=period_end,
            )
            if daily_weather.empty:
                return self._field_result(
                    field,
                    warnings=FarmAtlasWarning(
                        message=f"No cached weather data found for field {field.name}.",
                        code="NO_CACHED_WEATHER",
                    ),
                    status="skipped",
                    metadata={"source": "computed_from_weather_cache"},
                )

            soil_water_estimate = estimate_available_water_storage_capacity(
                soil_type=field.soil_type,
                soil_weight=field.soil_weight,
                humus_pct=field.humus_pct,
                effective_root_depth_cm=field.effective_root_depth_cm,
            )
            daily_weather = self._prepare_daily_weather_for_field(field, daily_weather)
            field_irrigation = FieldIrrigation.from_list(irrigation_events)
            water_balance = calculate_water_balance(
                nfk_total_mm=soil_water_estimate.nfk_total_mm,
                daily_weather=daily_weather,
                p_allowable=float(field.p_allowable),
                field_irrigation=field_irrigation,
                field_id=field.id,
            )
            return self._field_result(
                field,
                result=water_balance,
                metadata={
                    "source": "computed_from_weather_cache",
                    "forecast_days": int(forecast_days),
                },
            )
        except Exception as exc:
            logger.exception("Water balance calculation failed for field %s", field.name)
            return self._field_result(
                field,
                errors=FarmAtlasError.from_exception(
                    exc,
                    code="WATER_BALANCE_FAILED",
                    details={"year": year, "forecast_days": int(forecast_days)},
                ),
                metadata={"source": "computed_from_weather_cache"},
            )

    def calculate_fields(
        self,
        fields: list[FieldContext],
        *,
        year: int | None = None,
        forecast_days: int = 0,
    ) -> list[ApplicationFieldResult[pd.DataFrame]]:
        return [
            self.calculate_field(field, year=year, forecast_days=forecast_days)
            for field in fields
        ]

    def summary_from_result(self, result: ApplicationFieldResult[pd.DataFrame]) -> WaterBalanceSummary:
        if result.result is None or result.result.empty:
            return self._empty_summary(result.field_id)

        frame = result.result.sort_index()
        observed = frame[frame["value_type"] != "forecast"] if "value_type" in frame.columns else frame
        source = observed if not observed.empty else frame
        latest = source.iloc[-1]
        as_of = pd.Timestamp(source.index[-1]).date()
        return WaterBalanceSummary(
            field_id=result.field_id,
            as_of=as_of,
            current_water_deficit=float(latest["water_deficit"]),
            current_soil_water_content=float(latest["soil_water_content"]),
            available_water_storage=float(latest["available_water_storage"]),
            readily_available_water=None
            if pd.isna(latest.get("readily_available_water"))
            else float(latest["readily_available_water"]),
            below_raw=None if pd.isna(latest.get("below_raw")) else bool(latest["below_raw"]),
            safe_ratio=None if pd.isna(latest.get("safe_ratio")) else float(latest["safe_ratio"]),
        )

    def get_summary_for_field(
        self,
        field: FieldContext,
        *,
        year: int | None = None,
    ) -> WaterBalanceSummary:
        return self.summary_from_result(self.calculate_field(field, year=year, forecast_days=0))

    def get_summaries(
        self,
        fields: list[FieldContext],
        *,
        year: int | None = None,
    ) -> list[WaterBalanceSummary]:
        return [
            self.summary_from_result(result)
            for result in self.calculate_fields(fields, year=year, forecast_days=0)
        ]
