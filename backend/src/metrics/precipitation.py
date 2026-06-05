import datetime

import pandas as pd

from .periods import normalize_period


def calculate_precipitation_sum(
    daily_weather: pd.DataFrame,
    start_date: datetime.date | str,
    end_date: datetime.date | str | None = None,
    *,
    precipitation_column: str = "precipitation",
    include_start: bool = False,
) -> float:
    if precipitation_column not in daily_weather.columns:
        raise KeyError(f"daily_weather must contain '{precipitation_column}'")

    start, end = normalize_period(start_date, end_date, include_start=include_start)
    frame = daily_weather.copy()
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"]).dt.date
    elif isinstance(frame.index, pd.DatetimeIndex):
        dates = frame.index.date
    else:
        raise KeyError("daily_weather must have a 'date' column or DatetimeIndex")

    mask = (dates >= start) & (dates <= end)
    return float(pd.to_numeric(frame.loc[mask, precipitation_column], errors="coerce").fillna(0.0).sum())
