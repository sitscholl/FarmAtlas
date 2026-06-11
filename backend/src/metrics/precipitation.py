import datetime

import pandas as pd

from ..weather_frame import WeatherFrame


def _is_date_only(value: datetime.date | datetime.datetime | str | pd.Timestamp) -> bool:
    if isinstance(value, datetime.datetime):
        return False
    if isinstance(value, datetime.date):
        return True
    text = str(value)
    return "T" not in text and ":" not in text and len(text.strip()) <= 10


def _timestamps(weather: WeatherFrame) -> pd.Series:
    frame = weather.data
    if "timestamp" in frame.columns:
        return pd.to_datetime(frame["timestamp"])
    if isinstance(frame.index, pd.DatetimeIndex):
        return pd.Series(frame.index, index=frame.index)
    raise KeyError("weather.data must have a 'timestamp' column or DatetimeIndex")


def _timestamp_mask(
    weather: WeatherFrame,
    start_date: datetime.date | datetime.datetime | str,
    end_date: datetime.date | datetime.datetime | str | None,
    *,
    include_start: bool,
) -> pd.Series:
    timestamps = _timestamps(weather)
    tz = timestamps.dt.tz
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp.now(tz=tz) if end_date is None else pd.Timestamp(end_date)
    if tz is not None:
        start_ts = start_ts.tz_localize(tz) if start_ts.tz is None else start_ts.tz_convert(tz)
        end_ts = end_ts.tz_localize(tz) if end_ts.tz is None else end_ts.tz_convert(tz)

    if _is_date_only(start_date) and not include_start:
        start_ts = start_ts + pd.Timedelta(days=1)
        lower_mask = timestamps >= start_ts
    else:
        lower_mask = timestamps >= start_ts if include_start else timestamps > start_ts

    if end_date is not None and _is_date_only(end_date):
        upper_mask = timestamps < end_ts + pd.Timedelta(days=1)
    else:
        upper_mask = timestamps <= end_ts

    return lower_mask & upper_mask


def calculate_precipitation_sum(
    weather: WeatherFrame,
    start_date: datetime.date | datetime.datetime | str,
    end_date: datetime.date | datetime.datetime | str | None = None,
    *,
    precipitation_column: str = "precipitation",
    include_start: bool = False,
) -> float:
    if precipitation_column not in weather.data.columns:
        raise KeyError(f"weather.data must contain '{precipitation_column}'")

    mask = _timestamp_mask(weather, start_date, end_date, include_start=include_start)
    return float(pd.to_numeric(weather.data.loc[mask, precipitation_column], errors="coerce").fillna(0.0).sum())
