import datetime
import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd

from .database.db import Database
from .domain.field import FieldContext
from .meteo.load import MeteoLoader
from .meteo.resample import MeteoResampler
from .meteo.validate import MeteoValidator
from .weather_frame import WeatherFrame


logger = logging.getLogger(__name__)


STATION_HOURLY_VALUE_COLUMNS = [
    "precipitation",
    "tair_2m",
    "relative_humidity",
    "wind_speed",
    "wind_gust",
    "air_pressure",
    "sun_duration",
    "solar_radiation",
]

@dataclass(frozen=True)
class WeatherRefreshResult:
    source_provider: str
    source_station: str
    start: pd.Timestamp
    end: pd.Timestamp
    upserted_count: int


@dataclass
class FieldWeatherCacheService:
    db: Database
    meteo_loader: MeteoLoader
    meteo_validator: MeteoValidator
    meteo_resampler: MeteoResampler
    timezone: ZoneInfo
    min_sample_size: int = 1
    hourly_min_sample_size: int = 1
    default_max_age: datetime.timedelta = datetime.timedelta(hours=3)
    freshness_grace: datetime.timedelta = datetime.timedelta(minutes=10)
    refresh_lookback: datetime.timedelta = datetime.timedelta(days=2)

    def _to_timestamp(self, value: datetime.datetime | datetime.date | str | pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tz is None:
            return ts.tz_localize(self.timezone)
        return ts.tz_convert(self.timezone)

    def _normalize_hourly_window(
        self,
        start: datetime.datetime | datetime.date | str | pd.Timestamp,
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        start_ts = self._to_timestamp(start).floor("h")
        end_ts = self._to_timestamp(end)
        end_ts = end_ts if end_ts == end_ts.floor("h") else end_ts.ceil("h")
        if start_ts >= end_ts:
            raise ValueError("start must be before end")
        return start_ts, end_ts

    def _rows_to_hourly_dataframe(self, rows) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()

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
                    "source_provider": row.source_provider,
                    "source_station": row.source_station,
                    "value_type": row.value_type,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]
        )
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        if frame["timestamp"].dt.tz is None:
            frame["timestamp"] = frame["timestamp"].dt.tz_localize(self.timezone)
        else:
            frame["timestamp"] = frame["timestamp"].dt.tz_convert(self.timezone)
        frame["updated_at"] = pd.to_datetime(frame["updated_at"], utc=True)
        for column in STATION_HOURLY_VALUE_COLUMNS:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame.set_index("timestamp").sort_index()

    def _read_station_hourly(
        self,
        *,
        provider: str,
        station: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        with self.db.session_scope() as session:
            rows = self.db.field_weather.list_station_hourly(
                session,
                provider=provider,
                station=station,
                start=start,
                end=end,
            )
        return self._rows_to_hourly_dataframe(rows)

    def _prepare_hourly_weather(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data.copy()

        frame = data.reset_index()
        if "index" in frame.columns and "datetime" not in frame.columns:
            frame = frame.rename(columns={"index": "datetime"})

        groupby_cols = [column for column in ("station_id", "model") if column in frame.columns]
        keep_cols = [
            column
            for column in ["datetime", *groupby_cols, *STATION_HOURLY_VALUE_COLUMNS]
            if column in frame.columns
        ]
        frame = frame[keep_cols]
        hourly = self.meteo_resampler.apply_resampling(
            frame,
            freq="1h",
            groupby_cols=groupby_cols,
            min_sample_size=self.hourly_min_sample_size,
        )
        return hourly.set_index("datetime").sort_index()

    def _build_station_hourly_cache_frame(
        self,
        *,
        provider: str,
        station: str,
        hourly: pd.DataFrame,
        value_type: str | None = None,
    ) -> pd.DataFrame:
        if hourly.empty:
            return hourly.copy()

        frame = pd.DataFrame(index=hourly.index)
        frame["source_provider"] = provider
        frame["source_station"] = station

        for column in STATION_HOURLY_VALUE_COLUMNS:
            if column == "precipitation":
                frame[column] = (
                    pd.to_numeric(hourly[column], errors="coerce")
                    if column in hourly.columns
                    else None
                )
                continue
            frame[column] = pd.to_numeric(hourly[column], errors="coerce") if column in hourly.columns else None

        if value_type is not None:
            frame["value_type"] = value_type
        elif "model" in hourly.columns:
            frame["value_type"] = hourly["model"].eq("observation").map({True: "observed", False: "forecast"})
        else:
            frame["value_type"] = "observed"
        frame["timestamp"] = pd.to_datetime(frame.index)
        return frame

    def refresh_station_hourly(
        self,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | str | pd.Timestamp,
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
        value_type: str | None = None,
    ) -> WeatherRefreshResult:
        start_ts, end_ts = self._normalize_hourly_window(start, end)

        meteo_data = self.meteo_loader.query(
            provider=provider,
            station_ids=[station],
            start=start_ts,
            end=end_ts,
        )
        validated = self.meteo_validator.validate(meteo_data)
        station_data = validated.get_station_data(station)
        if station_data is None:
            raise ValueError(f"No meteo station data available for station {station}")

        hourly = self._prepare_hourly_weather(station_data.data)
        cache_frame = self._build_station_hourly_cache_frame(
            provider=provider,
            station=station,
            hourly=hourly,
            value_type=value_type,
        )
        with self.db.session_scope() as session:
            self.db.field_weather.upsert_station_metadata(
                session,
                self.db.engine,
                provider=provider,
                station=station,
                longitude=station_data.x,
                latitude=station_data.y,
                crs=station_data.crs,
                elevation=station_data.elevation,
            )
            upserted_count = self.db.field_weather.add_station_hourly(
                session,
                self.db.engine,
                cache_frame,
                provider=provider,
                station=station,
            )
        return WeatherRefreshResult(
            source_provider=provider,
            source_station=station,
            start=start_ts,
            end=end_ts,
            upserted_count=upserted_count,
        )

    def clear_station_hourly_cache(
        self,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | str | pd.Timestamp | None = None,
        end: datetime.datetime | datetime.date | str | pd.Timestamp | None = None,
        value_type: str | None = None,
    ) -> int:
        start_ts = None if start is None else self._to_timestamp(start)
        end_ts = None if end is None else self._to_timestamp(end)
        if start_ts is not None and end_ts is not None and start_ts >= end_ts:
            raise ValueError("start must be before end")

        with self.db.session_scope() as session:
            return self.db.field_weather.clear_station_hourly(
                session,
                provider=provider,
                station=station,
                start=start_ts,
                end=end_ts,
                value_type=value_type,
            )

    def _refresh_start_for_cache_state(
        self,
        cached: pd.DataFrame,
        *,
        start: pd.Timestamp,
        end: pd.Timestamp,
        max_age: datetime.timedelta | None,
        force: bool,
    ) -> pd.Timestamp | None:
        if force or cached.empty:
            return start

        expected_index = pd.date_range(start=start, end=end - pd.Timedelta(hours=1), freq="1h", tz=self.timezone)
        cached_index = cached.index.unique()
        missing_index = expected_index.difference(cached_index)
        tail_start = max(start, end - pd.Timedelta(self.refresh_lookback))

        if len(missing_index) > 0:
            return min(pd.Timestamp(missing_index.min()), tail_start)

        if max_age is None:
            return None

        tail = cached.loc[cached.index >= tail_start]
        if tail.empty:
            return tail_start

        freshness_window = pd.Timedelta(max_age)
        if max_age > datetime.timedelta(0):
            freshness_window += pd.Timedelta(self.freshness_grace)

        newest_update = pd.to_datetime(tail["updated_at"], utc=True).max()
        if newest_update < pd.Timestamp.now(tz="UTC") - freshness_window:
            return tail_start

        return None

    def ensure_station_hourly_weather(
        self,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | str | pd.Timestamp,
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
        max_age: datetime.timedelta | None = None,
        force: bool = False,
    ) -> WeatherFrame:
        start_ts, end_ts = self._normalize_hourly_window(start, end)
        max_age = self.default_max_age if max_age is None else max_age

        cached = self._read_station_hourly(
            provider=provider,
            station=station,
            start=start_ts,
            end=end_ts,
        )
        refreshed = False
        refresh_start = self._refresh_start_for_cache_state(
            cached,
            start=start_ts,
            end=end_ts,
            max_age=max_age,
            force=force,
        )
        if refresh_start is not None:
            self.refresh_station_hourly(
                provider=provider,
                station=station,
                start=refresh_start,
                end=end_ts,
            )
            refreshed = True
            cached = self._read_station_hourly(
                provider=provider,
                station=station,
                start=start_ts,
                end=end_ts,
            )

        return WeatherFrame(
            data=cached,
            resolution="1h",
            start=start_ts,
            end=end_ts,
            source_provider=provider,
            source_station=station,
            refreshed=refreshed,
            max_age=max_age,
        )

    def ensure_fields_hourly_weather(
        self,
        fields: list[FieldContext],
        *,
        start: datetime.datetime | datetime.date | str | pd.Timestamp | dict[int, datetime.datetime | datetime.date | str | pd.Timestamp],
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
        max_age: datetime.timedelta | None = None,
        force: bool = False,
    ) -> dict[int, WeatherFrame]:
        if not fields:
            return {}

        end_ts = self._normalize_hourly_window(self._field_start(fields[0], start), end)[1]
        groups: dict[tuple[str, str], list[FieldContext]] = {}
        for field in fields:
            groups.setdefault((field.reference_provider, field.reference_station), []).append(field)

        station_frames: dict[tuple[str, str], WeatherFrame] = {}
        for (provider, station), station_fields in groups.items():
            group_start = min(
                self._normalize_hourly_window(self._field_start(field, start), end_ts)[0]
                for field in station_fields
            )
            station_frames[(provider, station)] = self.ensure_station_hourly_weather(
                provider=provider,
                station=station,
                start=group_start,
                end=end_ts,
                max_age=max_age,
                force=force,
            )

        result: dict[int, WeatherFrame] = {}
        for field in fields:
            field_start = self._normalize_hourly_window(self._field_start(field, start), end_ts)[0]
            station_weather = station_frames[(field.reference_provider, field.reference_station)]
            frame = station_weather.data.loc[
                (station_weather.data.index >= field_start) & (station_weather.data.index < end_ts)
            ].copy()
            result[field.id] = WeatherFrame(
                data=frame,
                resolution=station_weather.resolution,
                start=field_start,
                end=end_ts,
                source_provider=field.reference_provider,
                source_station=field.reference_station,
                refreshed=station_weather.refreshed,
                max_age=station_weather.max_age,
            )
        return result

    def _field_start(
        self,
        field: FieldContext,
        start: datetime.datetime | datetime.date | str | pd.Timestamp | dict[int, datetime.datetime | datetime.date | str | pd.Timestamp],
    ) -> datetime.datetime | datetime.date | str | pd.Timestamp:
        if isinstance(start, dict):
            return start[field.id]
        return start

    def get_field_hourly_weather(
        self,
        field: FieldContext,
        *,
        start: datetime.datetime | datetime.date | str | pd.Timestamp,
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
        ensure: bool = True,
        max_age: datetime.timedelta | None = None,
    ) -> WeatherFrame:
        if ensure:
            return self.ensure_station_hourly_weather(
                provider=field.reference_provider,
                station=field.reference_station,
                start=start,
                end=end,
                max_age=max_age,
            )

        start_ts, end_ts = self._normalize_hourly_window(start, end)
        frame = self._read_station_hourly(
            provider=field.reference_provider,
            station=field.reference_station,
            start=start_ts,
            end=end_ts,
        )
        return WeatherFrame(
            data=frame,
            resolution="1h",
            start=start_ts,
            end=end_ts,
            source_provider=field.reference_provider,
            source_station=field.reference_station,
            refreshed=False,
            max_age=max_age,
        )

    def get_station_hourly_weather(
        self,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | str | pd.Timestamp,
        end: datetime.datetime | datetime.date | str | pd.Timestamp,
    ) -> WeatherFrame:
        start_ts, end_ts = self._normalize_hourly_window(start, end)
        frame = self._read_station_hourly(
            provider=provider,
            station=station,
            start=start_ts,
            end=end_ts,
        )
        return WeatherFrame(
            data=frame,
            resolution="1h",
            start=start_ts,
            end=end_ts,
            source_provider=provider,
            source_station=station,
            refreshed=False,
            max_age=None,
        )

    def aggregate_daily(self, hourly_weather: WeatherFrame) -> WeatherFrame:
        if hourly_weather.resolution != "1h":
            raise ValueError(f"aggregate_daily expects 1h weather, got {hourly_weather.resolution!r}")
        if hourly_weather.empty:
            return WeatherFrame(
                data=pd.DataFrame(),
                resolution="1D",
                start=hourly_weather.start,
                end=hourly_weather.end,
                source_provider=hourly_weather.source_provider,
                source_station=hourly_weather.source_station,
                refreshed=hourly_weather.refreshed,
                max_age=hourly_weather.max_age,
            )

        frame = hourly_weather.data.reset_index()
        if "timestamp" not in frame.columns:
            frame = frame.rename(columns={frame.columns[0]: "timestamp"})
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        if frame["timestamp"].dt.tz is None:
            frame["timestamp"] = frame["timestamp"].dt.tz_localize(self.timezone)
        else:
            frame["timestamp"] = frame["timestamp"].dt.tz_convert(self.timezone)

        groupby_cols = [
            column
            for column in ("source_provider", "source_station", "value_type")
            if column in frame.columns
        ]
        daily = self.meteo_resampler.apply_resampling(
            frame,
            freq="1D",
            datetime_col="timestamp",
            groupby_cols=groupby_cols,
            min_sample_size=self.min_sample_size,
        )
        return WeatherFrame(
            data=daily,
            resolution="1D",
            start=hourly_weather.start,
            end=hourly_weather.end,
            source_provider=hourly_weather.source_provider,
            source_station=hourly_weather.source_station,
            refreshed=hourly_weather.refreshed,
            max_age=hourly_weather.max_age,
        )

    def refresh_field(
        self,
        field: FieldContext,
        *,
        start: datetime.datetime | datetime.date | str,
        end: datetime.datetime | datetime.date | str,
    ) -> int:
        result = self.refresh_station_hourly(
            provider=field.reference_provider,
            station=field.reference_station,
            start=start,
            end=end,
        )
        return result.upserted_count

    def cleanup_station_hourly_cache(
        self,
        *,
        older_than: datetime.timedelta,
        now: datetime.datetime | pd.Timestamp | None = None,
    ) -> int:
        if older_than <= datetime.timedelta(0):
            raise ValueError("older_than must be greater than zero")

        now_ts = pd.Timestamp.now(tz=self.timezone) if now is None else self._to_timestamp(now)
        cutoff = now_ts - pd.Timedelta(older_than)
        with self.db.session_scope() as session:
            return self.db.field_weather.delete_station_hourly_before(
                session,
                cutoff=cutoff,
            )
