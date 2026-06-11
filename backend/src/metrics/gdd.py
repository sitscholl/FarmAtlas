import datetime

import pandas as pd

from ..weather_frame import WeatherFrame
from .precipitation import _timestamp_mask


def _resolution_timedelta(resolution: str) -> pd.Timedelta:
    try:
        return pd.Timedelta(resolution)
    except ValueError as exc:
        raise ValueError(f"Unsupported weather resolution {resolution!r}") from exc


def calculate_gdd_sum(
    weather: WeatherFrame,
    start_date: datetime.date | datetime.datetime | str,
    end_date: datetime.date | datetime.datetime | str | None = None,
    *,
    base_temperature: float,
    temperature_column: str = "tair_2m",
    include_start: bool = False,
) -> float:
    if temperature_column not in weather.data.columns:
        raise KeyError(f"weather.data must contain '{temperature_column}'")

    mask = _timestamp_mask(weather, start_date, end_date, include_start=include_start)
    heat = (
        pd.to_numeric(weather.data.loc[mask, temperature_column], errors="coerce") - float(base_temperature)
    ).clip(lower=0).fillna(0.0)

    resolution_delta = _resolution_timedelta(weather.resolution)
    if resolution_delta <= pd.Timedelta(0):
        raise ValueError(f"Weather resolution must be positive, got {weather.resolution!r}")
    if resolution_delta < pd.Timedelta(days=1):
        return float(heat.sum() * (resolution_delta / pd.Timedelta(days=1)))
    if resolution_delta == pd.Timedelta(days=1):
        return float(heat.sum())

    raise ValueError(f"GDD calculation does not support weather resolution {weather.resolution!r}")
