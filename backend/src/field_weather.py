import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd

from .database.db import Database
from .field import FieldContext
from .meteo.load import MeteoLoader
from .meteo.resample import MeteoResampler
from .meteo.validate import MeteoValidator


@dataclass
class FieldWeatherCacheService:
    db: Database
    meteo_loader: MeteoLoader
    meteo_validator: MeteoValidator
    meteo_resampler: MeteoResampler
    timezone: ZoneInfo
    min_sample_size: int = 1

    def _to_timestamp(self, value: datetime.date | str) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tz is None:
            return ts.tz_localize(self.timezone)
        return ts.tz_convert(self.timezone)

    def _prepare_daily_weather(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data.copy()

        frame = data.reset_index()
        if "index" in frame.columns and "datetime" not in frame.columns:
            frame = frame.rename(columns={"index": "datetime"})

        groupby_cols = [column for column in ("station_id", "model") if column in frame.columns]
        daily = self.meteo_resampler.apply_resampling(
            frame,
            freq="D",
            groupby_cols=groupby_cols,
            min_sample_size=self.min_sample_size,
        )
        return daily.set_index("datetime").sort_index()

    def _build_cache_frame(self, field: FieldContext, daily: pd.DataFrame) -> pd.DataFrame:
        if daily.empty:
            return daily.copy()

        frame = pd.DataFrame(index=daily.index)
        frame["field_id"] = field.id
        frame["precipitation"] = (
            pd.to_numeric(daily["precipitation"], errors="coerce").fillna(0.0)
            if "precipitation" in daily.columns
            else 0.0
        )

        tmin = daily["tair_2m_min"] if "tair_2m_min" in daily.columns else daily.get("tair_2m")
        tmax = daily["tair_2m_max"] if "tair_2m_max" in daily.columns else daily.get("tair_2m")
        tmean = daily["tair_2m"] if "tair_2m" in daily.columns else None
        frame["tmin"] = None if tmin is None else pd.to_numeric(tmin, errors="coerce")
        frame["tmax"] = None if tmax is None else pd.to_numeric(tmax, errors="coerce")
        if tmean is None:
            frame["tmean"] = (frame["tmin"] + frame["tmax"]) / 2
        else:
            frame["tmean"] = pd.to_numeric(tmean, errors="coerce")

        frame["source_provider"] = field.reference_provider
        frame["source_station"] = field.reference_station
        if "model" in daily.columns:
            frame["value_type"] = daily["model"].eq("observation").map({True: "observed", False: "forecast"})
        else:
            frame["value_type"] = "observed"
        frame["date"] = pd.to_datetime(frame.index).date
        return frame

    def refresh_field(
        self,
        field: FieldContext,
        *,
        start: datetime.date | str,
        end: datetime.date | str,
    ) -> int:
        start_ts = self._to_timestamp(start).floor("D")
        end_ts = self._to_timestamp(end).floor("D")
        if start_ts >= end_ts:
            raise ValueError("start must be before end")

        meteo_data = self.meteo_loader.query(
            provider=field.reference_provider,
            station_ids=[field.reference_station],
            start=start_ts,
            end=end_ts,
        )
        validated = self.meteo_validator.validate(meteo_data)
        station = validated.get_station_data(field.reference_station)
        if station is None:
            raise ValueError(f"No meteo station data available for station {field.reference_station}")

        daily = self._prepare_daily_weather(station.data)
        cache_frame = self._build_cache_frame(field, daily)
        with self.db.session_scope() as session:
            return self.db.field_weather.add(session, self.db.engine, cache_frame, field_id=field.id)
