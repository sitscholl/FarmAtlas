import datetime

import pandas as pd

from .periods import normalize_period


def daily_gdd(
    tmin: pd.Series,
    tmax: pd.Series,
    *,
    base_temperature: float,
) -> pd.Series:
    tmean = (pd.to_numeric(tmin, errors="coerce") + pd.to_numeric(tmax, errors="coerce")) / 2
    return (tmean - float(base_temperature)).clip(lower=0)


def calculate_gdd_sum(
    daily_weather: pd.DataFrame,
    start_date: datetime.date | str,
    end_date: datetime.date | str | None = None,
    *,
    base_temperature: float,
    tmin_column: str = "tmin",
    tmax_column: str = "tmax",
    include_start: bool = False,
) -> float:
    missing_columns = [column for column in (tmin_column, tmax_column) if column not in daily_weather.columns]
    if missing_columns:
        raise KeyError(f"daily_weather is missing required columns: {', '.join(missing_columns)}")

    start, end = normalize_period(start_date, end_date, include_start=include_start)
    frame = daily_weather.copy()
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"]).dt.date
    elif isinstance(frame.index, pd.DatetimeIndex):
        dates = frame.index.date
    else:
        raise KeyError("daily_weather must have a 'date' column or DatetimeIndex")

    mask = (dates >= start) & (dates <= end)
    return float(
        daily_gdd(
            frame.loc[mask, tmin_column],
            frame.loc[mask, tmax_column],
            base_temperature=base_temperature,
        ).sum()
    )
