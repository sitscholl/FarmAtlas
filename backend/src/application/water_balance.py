import pandas as pd

from dataclasses import dataclass
import logging

from ..database.db import Database
from ..et.et_correction import ETCorrection
from ..field import FieldContext
from ..field_weather import FieldWeatherCacheService
from ..irrigation import FieldIrrigation
from ..calculation.soil_water import estimate_available_water_storage_capacity
from ..weather_frame import WeatherFrame

logger = logging.getLogger(__name__)

@dataclass
class WaterBalanceService:
    db: Database
    weather_cache: FieldWeatherCacheService
    et_corrector: ETCorrection
    timezone: ZoneInfo
    forecast_provider: str = "open-meteo"

    def _empty_result(
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
