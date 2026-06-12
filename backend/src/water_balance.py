from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from .database.db import Database
from .et.et_correction import ETCorrection
from .field import FieldContext
from .field_weather import FieldWeatherCacheService
from .irrigation import FieldIrrigation
from .schemas import WaterBalanceSummary
from .water_content import estimate_available_water_storage_capacity
from .weather_frame import WeatherFrame
from .workflows.base import WorkflowError, WorkflowFieldResult, WorkflowWarning

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
class WaterBalanceCalculator:
    def calculate(
        self,
        field: FieldContext,
        daily_weather: pd.DataFrame,
        *,
        field_irrigation: FieldIrrigation | None = None,
        initial_storage: float | None = None,
    ) -> pd.DataFrame:
        if daily_weather is None or daily_weather.empty:
            raise ValueError("Daily weather cannot be empty when calculating the water balance.")
        if not isinstance(daily_weather.index, pd.DatetimeIndex):
            raise TypeError("Daily weather index must be a pandas DatetimeIndex.")

        missing_parameters = missing_soil_parameters(field)
        if missing_parameters:
            raise ValueError(
                f"Field {field.name} is missing required soil parameters: {', '.join(missing_parameters)}"
            )

        data = daily_weather.sort_index().copy()
        if "precipitation" not in data.columns:
            raise KeyError("Daily weather must contain a 'precipitation' column.")

        et_column = "et0_corrected" if "et0_corrected" in data.columns else "et0" if "et0" in data.columns else None
        if et_column is None or data[et_column].isna().any():
            raise KeyError("Daily weather must contain complete 'et0_corrected' or 'et0' values.")

        precipitation = pd.to_numeric(data["precipitation"], errors="coerce").fillna(0.0)
        evapotranspiration = pd.to_numeric(data[et_column], errors="coerce").fillna(0.0)
        irrigation = (
            pd.Series(0.0, index=data.index, dtype=float)
            if field_irrigation is None
            else field_irrigation.to_dataframe(data.index, fill_value=0.0)
        )

        incoming = precipitation + irrigation
        net = incoming - evapotranspiration
        soil_water_estimate = estimate_available_water_storage_capacity(
            soil_type=field.soil_type,
            soil_weight=field.soil_weight,
            humus_pct=field.humus_pct,
            effective_root_depth_cm=field.effective_root_depth_cm,
        )
        available_water_storage = soil_water_estimate.nfk_total_mm

        soil_water_content: list[float] = []
        current_water_content = (
            available_water_storage
            if initial_storage is None
            else max(0.0, min(available_water_storage, initial_storage))
        )
        for delta in net:
            current_water_content = max(0.0, min(available_water_storage, current_water_content + delta))
            soil_water_content.append(current_water_content)

        water_balance = pd.DataFrame(
            {
                "precipitation": precipitation,
                "irrigation": irrigation,
                "evapotranspiration": evapotranspiration,
                "incoming": incoming,
                "net": net,
                "soil_water_content": soil_water_content,
            },
            index=data.index,
        )
        water_balance["available_water_storage"] = available_water_storage
        water_balance["water_deficit"] = available_water_storage - water_balance["soil_water_content"]
        water_balance["field_id"] = field.id
        if "kc" in data.columns:
            water_balance["kc"] = data["kc"]

        readily_available_water = float(field.p_allowable) * available_water_storage
        water_balance["readily_available_water"] = readily_available_water

        trigger_level = available_water_storage - readily_available_water
        water_balance["below_raw"] = water_balance["soil_water_content"] < trigger_level
        water_balance["safe_ratio"] = (
            water_balance["soil_water_content"] - trigger_level
        ) / readily_available_water

        for column in ("model", "station_id", "source_provider", "source_station"):
            if column in data.columns:
                water_balance[column] = data[column]

        if "value_type" in data.columns:
            water_balance["value_type"] = data["value_type"].fillna("observed")
        elif "model" in data.columns:
            water_balance["value_type"] = data["model"].eq("observation").map({True: "observed", False: "forecast"})
        else:
            water_balance["value_type"] = "observed"

        return water_balance


@dataclass
class WaterBalanceService:
    db: Database
    weather_cache: FieldWeatherCacheService
    et_corrector: ETCorrection
    timezone: ZoneInfo
    forecast_provider: str = "open-meteo"
    calculator: WaterBalanceCalculator = field(default_factory=WaterBalanceCalculator)

    workflow_name: str = "water_balance"

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
        warnings: list[WorkflowWarning] | WorkflowWarning | None = None,
        errors: list[WorkflowError] | WorkflowError | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowFieldResult[pd.DataFrame]:
        return WorkflowFieldResult(
            workflow_name=self.workflow_name,
            field_id=field.id,
            field_name=field.name,
            result=result,
            warnings=warnings,
            errors=errors,
            status=status,
            metadata=metadata or {},
        )

    def _period_end(self, *, forecast_days: int = 0, as_of: pd.Timestamp | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
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

        if "datetime" in daily.columns:
            daily["datetime"] = pd.to_datetime(daily["datetime"])
            daily = daily.set_index("datetime")
        daily = daily.sort_index()
        return daily

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
    ) -> WorkflowFieldResult[pd.DataFrame]:
        year = year or pd.Timestamp.now(tz=self.timezone).year
        observe_end, period_end = self._period_end(forecast_days=forecast_days)
        if period_end <= observe_end:
            period_end = observe_end

        try:
            with self.db.session_scope() as session:
                first_irrigation = self.db.irrigation.get_first_for_year(session, field_id=field.id, year=year)
                if first_irrigation is None:
                    return self._field_result(
                        field,
                        warnings=WorkflowWarning(
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
                    warnings=WorkflowWarning(
                        message=f"No cached weather data found for field {field.name}.",
                        code="NO_CACHED_WEATHER",
                    ),
                    status="skipped",
                    metadata={"source": "computed_from_weather_cache"},
                )

            daily_weather = self._prepare_daily_weather_for_field(field, daily_weather)
            field_irrigation = FieldIrrigation.from_list(irrigation_events)
            water_balance = self.calculator.calculate(
                field,
                daily_weather,
                field_irrigation=field_irrigation,
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
                errors=WorkflowError.from_exception(
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
    ) -> list[WorkflowFieldResult[pd.DataFrame]]:
        return [
            self.calculate_field(field, year=year, forecast_days=forecast_days)
            for field in fields
        ]

    def summary_from_result(self, result: WorkflowFieldResult[pd.DataFrame]) -> WaterBalanceSummary:
        if result.result is None or result.result.empty:
            return self._empty_summary(result.field_id)

        frame = result.result.sort_index()
        observed = frame[frame.get("value_type", "observed") != "forecast"] if "value_type" in frame.columns else frame
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
