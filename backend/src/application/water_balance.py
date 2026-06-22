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
from ..et.base import ET0Calculator
from ..et.et_correction import ETCorrection
from ..domain.field import FieldContext
from ..domain.irrigation import FieldIrrigation
from ..field_weather import FieldWeatherCacheService
from ..meteo.station import Station
from ..results import FarmAtlasError, FarmAtlasWarning
from ..weather_frame import WeatherFrame
from ..weather_quality import aggregate_missing_weather_warnings, build_missing_weather_warning

logger = logging.getLogger(__name__)

WATER_BALANCE_EVAPOTRANSPIRATION_WARNING_CODES = {
    "WATER_BALANCE_ET_INPUTS_INCOMPLETE",
    "WATER_BALANCE_ET0_INCOMPLETE",
    "WATER_BALANCE_ET_CORRECTED_INCOMPLETE",
}


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


@dataclass(slots=True)
class DailyWeatherResult:
    data: pd.DataFrame
    warnings: list[FarmAtlasWarning]
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class PreparedDailyWeatherResult:
    data: pd.DataFrame
    warnings: list[FarmAtlasWarning]
    metadata: dict[str, Any] | None = None


@dataclass
class WaterBalanceService:
    db: Database
    weather_cache: FieldWeatherCacheService
    et_calculator: ET0Calculator
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
    ) -> DailyWeatherResult:
        hourly_frames: list[pd.DataFrame] = []
        warnings: list[FarmAtlasWarning] = []
        metadata: dict[str, Any] = {}

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
            else:
                warnings.append(
                    FarmAtlasWarning(
                        message=(
                            "Forecast weather cache is missing. Refresh the weather cache "
                            "to show the forecast part of the water-balance chart."
                        ),
                        code="FORECAST_CACHE_MISSING",
                        details={
                            "provider": self.forecast_provider,
                            "station": field.reference_station,
                            "start": observe_end.isoformat(),
                            "end": period_end.isoformat(),
                        },
                    )
                )

        if not hourly_frames:
            return DailyWeatherResult(data=pd.DataFrame(), warnings=warnings, metadata=metadata)

        hourly = pd.concat(hourly_frames).sort_index()
        hourly = hourly.loc[(hourly.index >= start) & (hourly.index < period_end)]
        if hourly.empty:
            return DailyWeatherResult(data=pd.DataFrame(), warnings=warnings, metadata=metadata)

        hourly_completeness = WeatherFrame(
            data=hourly,
            resolution="1h",
            start=start,
            end=period_end,
            source_provider=field.reference_provider,
            source_station=field.reference_station,
        ).completeness(["precipitation"])
        metadata["hourly_weather_completeness"] = hourly_completeness.to_dict()
        precipitation_warning = build_missing_weather_warning(
            hourly_completeness,
            columns=["precipitation"],
            code="WATER_BALANCE_PRECIPITATION_INCOMPLETE",
            calculation="water_balance",
            subject="precipitation",
            assumption="missing_precipitation_treated_as_zero",
            impact="Missing precipitation is treated as 0.0 mm.",
        )
        if precipitation_warning is not None:
            warnings.append(precipitation_warning)

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
            return DailyWeatherResult(data=daily, warnings=warnings, metadata=metadata)

        datetime_column = "datetime" if "datetime" in daily.columns else "timestamp" if "timestamp" in daily.columns else None
        if datetime_column is not None:
            daily[datetime_column] = pd.to_datetime(daily[datetime_column])
            daily = daily.set_index(datetime_column)
        elif not isinstance(daily.index, pd.DatetimeIndex):
            raise TypeError("Daily cached weather must contain a datetime or timestamp column.")
        daily = daily.sort_index()
        daily_completeness = WeatherFrame(
            data=daily,
            resolution="1D",
            start=start.floor("D"),
            end=period_end,
            source_provider=field.reference_provider,
            source_station=field.reference_station,
        ).completeness(["precipitation"])
        metadata["daily_weather_completeness"] = daily_completeness.to_dict()
        return DailyWeatherResult(data=daily, warnings=warnings, metadata=metadata)

    def _station_for_daily_weather(
        self,
        field: FieldContext,
        *,
        provider: str,
        station: str,
        daily_weather: pd.DataFrame,
    ) -> Station:
        with self.db.session_scope() as session:
            metadata = self.db.field_weather.get_station_metadata(
                session,
                provider=provider,
                station=station,
            )
            if metadata is None:
                raise KeyError(
                    f"No cached station metadata found for {provider}/{station}. "
                    "Refresh the weather cache once before calculating water balance."
                )
            longitude = metadata.longitude
            latitude = metadata.latitude
            crs = metadata.crs
            elevation = metadata.elevation

        return Station(
            id=station,
            x=float(longitude),
            y=float(latitude),
            crs=int(crs),
            elevation=field.elevation if elevation is None else float(elevation),
            data=daily_weather,
        )

    def _calculate_et0_for_daily_weather(
        self,
        field: FieldContext,
        prepared: pd.DataFrame,
    ) -> PreparedDailyWeatherResult:
        if not isinstance(prepared.index, pd.DatetimeIndex):
            raise TypeError("Daily cached weather must use a pandas DatetimeIndex before ET0 calculation.")

        frame = prepared.drop(columns=["et0", "et0_corrected", "kc"], errors="ignore").copy()
        warnings: list[FarmAtlasWarning] = []
        metadata: dict[str, Any] = {}
        group_columns = [
            column
            for column in ("source_provider", "source_station")
            if column in frame.columns
        ]
        if len(group_columns) == 2:
            groups = frame.groupby(group_columns, dropna=False, sort=False)
        else:
            groups = [((field.reference_provider, field.reference_station), frame)]

        calculated_groups: list[pd.DataFrame] = []
        for key, group in groups:
            if len(group_columns) == 2:
                provider, station = key
            else:
                provider, station = field.reference_provider, field.reference_station

            provider = str(provider)
            station = str(station)
            group = group.copy()
            completeness = WeatherFrame(
                data=group,
                resolution="1D",
                start=pd.Timestamp(group.index.min()).normalize(),
                end=pd.Timestamp(group.index.max()).normalize() + pd.Timedelta(days=1),
                source_provider=provider,
                source_station=station,
            ).completeness(list(self.et_calculator.required_columns))
            metadata.setdefault("et_input_completeness", {})[f"{provider}/{station}"] = completeness.to_dict()
            missing_columns = [
                column
                for column, column_completeness in completeness.columns.items()
                if column_completeness.missing_count > 0
            ]
            if missing_columns:
                warning = build_missing_weather_warning(
                    completeness,
                    columns=missing_columns,
                    code="WATER_BALANCE_ET_INPUTS_INCOMPLETE",
                    calculation="water_balance",
                    subject="ET input",
                    assumption="missing_evapotranspiration_treated_as_zero",
                    impact="Affected evapotranspiration rows are treated as 0.0 mm.",
                )
                if warning is not None:
                    warning.details["provider"] = provider
                    warning.details["station"] = station
                    warnings.append(warning)

            if not self.et_calculator.can_calculate(group):
                group["et0"] = pd.NA
                warnings.append(
                    FarmAtlasWarning(
                        message=(
                            f"ET0 could not be calculated for {provider}/{station} because the cached weather "
                            "does not contain enough complete ET input rows. Affected rows are treated as 0.0 mm."
                        ),
                        code="WATER_BALANCE_ET0_UNAVAILABLE",
                        details={
                            "provider": provider,
                            "station": station,
                            "row_count": int(len(group.index)),
                            "assumption": "missing_evapotranspiration_treated_as_zero",
                        },
                    )
                )
            else:
                station_weather = self._station_for_daily_weather(
                    field,
                    provider=provider,
                    station=station,
                    daily_weather=group,
                )
                et0 = self.et_calculator.calculate(station_weather, correct=False)
                if "et0" not in et0.columns:
                    raise KeyError("ET0 calculator did not return an 'et0' column.")

                values = pd.to_numeric(et0["et0"], errors="coerce")
                if len(values.index) != len(group.index):
                    values = values.reindex(group.index)
                group["et0"] = values.to_numpy()

            missing_et0_count = int(pd.to_numeric(group["et0"], errors="coerce").isna().sum())
            if missing_et0_count > 0:
                et0_completeness = WeatherFrame(
                    data=group,
                    resolution="1D",
                    start=pd.Timestamp(group.index.min()).normalize(),
                    end=pd.Timestamp(group.index.max()).normalize() + pd.Timedelta(days=1),
                    source_provider=provider,
                    source_station=station,
                ).completeness(["et0"])
                warning = build_missing_weather_warning(
                    et0_completeness,
                    columns=["et0"],
                    code="WATER_BALANCE_ET0_INCOMPLETE",
                    calculation="water_balance",
                    subject="ET0",
                    assumption="missing_evapotranspiration_treated_as_zero",
                    impact="Affected evapotranspiration rows are treated as 0.0 mm.",
                )
                if warning is not None:
                    warning.details["provider"] = provider
                    warning.details["station"] = station
                    warnings.append(warning)
            calculated_groups.append(group)

        calculated = pd.concat(calculated_groups).sort_index()
        return PreparedDailyWeatherResult(data=calculated, warnings=warnings, metadata=metadata)

    def _prepare_daily_weather_for_field(
        self,
        field: FieldContext,
        daily_weather: pd.DataFrame,
    ) -> PreparedDailyWeatherResult:
        et_result = self._calculate_et0_for_daily_weather(field, daily_weather)
        prepared = self.et_corrector.apply_to_field(et_result.data, "et0", field)
        warnings = list(et_result.warnings)
        metadata = dict(et_result.metadata or {})
        missing_corrected_count = int(pd.to_numeric(prepared["et0_corrected"], errors="coerce").isna().sum())
        if missing_corrected_count > 0:
            completeness = WeatherFrame(
                data=prepared,
                resolution="1D",
                start=pd.Timestamp(prepared.index.min()).normalize(),
                end=pd.Timestamp(prepared.index.max()).normalize() + pd.Timedelta(days=1),
                source_provider=field.reference_provider,
                source_station=field.reference_station,
            ).completeness(["et0_corrected"])
            warning = build_missing_weather_warning(
                completeness,
                columns=["et0_corrected"],
                code="WATER_BALANCE_ET_CORRECTED_INCOMPLETE",
                calculation="water_balance",
                subject="field-specific evapotranspiration",
                assumption="missing_evapotranspiration_treated_as_zero",
                impact="Affected evapotranspiration rows are treated as 0.0 mm.",
            )
            if warning is not None:
                warnings.append(warning)
        metadata["et0_missing_count"] = int(pd.to_numeric(prepared["et0"], errors="coerce").isna().sum())
        metadata["et0_corrected_missing_count"] = missing_corrected_count
        warnings = aggregate_missing_weather_warnings(
            warnings,
            source_codes=WATER_BALANCE_EVAPOTRANSPIRATION_WARNING_CODES,
            code="WATER_BALANCE_EVAPOTRANSPIRATION_INCOMPLETE",
            calculation="water_balance",
            subject="evapotranspiration",
            assumption="missing_evapotranspiration_treated_as_zero",
            impact="Affected evapotranspiration rows are treated as 0.0 mm.",
        )
        return PreparedDailyWeatherResult(data=prepared, warnings=warnings, metadata=metadata)

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
            daily_weather_result = self._daily_weather(
                field,
                start=start,
                observe_end=observe_end,
                period_end=period_end,
            )
            daily_weather = daily_weather_result.data
            if daily_weather.empty:
                return self._field_result(
                    field,
                    warnings=[
                        *daily_weather_result.warnings,
                        FarmAtlasWarning(
                            message=f"No cached weather data found for field {field.name}.",
                            code="NO_CACHED_WEATHER",
                        ),
                    ],
                    status="skipped",
                    metadata={"source": "computed_from_weather_cache"},
                )

            soil_water_estimate = estimate_available_water_storage_capacity(
                soil_type=field.soil_type,
                soil_weight=field.soil_weight,
                humus_pct=field.humus_pct,
                effective_root_depth_cm=field.effective_root_depth_cm,
            )
            prepared_weather_result = self._prepare_daily_weather_for_field(field, daily_weather)
            daily_weather = prepared_weather_result.data
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
                warnings=[
                    *daily_weather_result.warnings,
                    *prepared_weather_result.warnings,
                ],
                metadata={
                    "source": "computed_from_weather_cache",
                    "forecast_days": int(forecast_days),
                    "weather_quality": daily_weather_result.metadata or {},
                    "et_quality": prepared_weather_result.metadata or {},
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
