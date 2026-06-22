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


def aggregate_missing_weather_warnings(
    warnings: Iterable[FarmAtlasWarning],
    *,
    source_codes: set[str],
    code: str,
    calculation: str,
    subject: str,
    assumption: str,
    impact: str,
) -> list[FarmAtlasWarning]:
    warnings = list(warnings)
    matching = [
        warning
        for warning in warnings
        if warning.code in source_codes
    ]
    if len(matching) <= 1:
        return warnings

    missing_count = sum(
        int(warning.details.get("missing_count", 0))
        for warning in matching
        if isinstance(warning.details.get("missing_count"), int)
    )
    if missing_count <= 0:
        return warnings

    columns = sorted(
        {
            str(column)
            for warning in matching
            for column in warning.details.get("columns", [])
        }
    )
    source_code_list = sorted(
        {
            warning.code
            for warning in matching
            if warning.code is not None
        }
    )
    aggregate = FarmAtlasWarning(
        message=(
            f"{missing_count} daily {subject} rows are missing for {calculation}. "
            f"{impact}"
        ),
        code=code,
        details={
            "category": "weather_quality",
            "calculation": calculation,
            "columns": columns,
            "missing_count": missing_count,
            "assumption": assumption,
            "source_codes": source_code_list,
            "source_warning_count": len(matching),
        },
    )

    result: list[FarmAtlasWarning] = []
    aggregate_inserted = False
    for warning in warnings:
        if warning.code in source_codes:
            if not aggregate_inserted:
                result.append(aggregate)
                aggregate_inserted = True
            continue
        result.append(warning)
    return result


def _resolution_label(resolution: str) -> str:
    normalized = resolution.strip().lower()
    if normalized in {"1h", "h", "hour", "hourly"}:
        return "hourly"
    if normalized in {"1d", "d", "day", "daily"}:
        return "daily"
    return resolution
