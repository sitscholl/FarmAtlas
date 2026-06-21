from __future__ import annotations

from typing import Iterable

from .results import FarmAtlasWarning
from .weather_frame import WeatherCompleteness


def missing_count_for_columns(
    completeness: WeatherCompleteness,
    columns: Iterable[str],
) -> int:
    return sum(
        completeness.columns[column].missing_count
        for column in columns
        if column in completeness.columns
    )


def build_missing_weather_warning(
    completeness: WeatherCompleteness,
    *,
    columns: list[str],
    code: str,
    calculation: str,
    subject: str,
    assumption: str,
    impact: str,
) -> FarmAtlasWarning | None:
    missing_count = missing_count_for_columns(completeness, columns)
    if missing_count <= 0:
        return None

    resolution_label = _resolution_label(completeness.resolution)
    return FarmAtlasWarning(
        message=(
            f"{missing_count} {resolution_label} {subject} rows are missing for {calculation}. "
            f"{impact}"
        ),
        code=code,
        details={
            "category": "weather_quality",
            "calculation": calculation,
            "columns": columns,
            "missing_count": missing_count,
            "assumption": assumption,
            "completeness": completeness.to_dict(),
        },
    )


def _resolution_label(resolution: str) -> str:
    normalized = resolution.strip().lower()
    if normalized in {"1h", "h", "hour", "hourly"}:
        return "hourly"
    if normalized in {"1d", "d", "day", "daily"}:
        return "daily"
    return resolution
