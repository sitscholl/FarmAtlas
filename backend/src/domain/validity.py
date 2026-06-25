from __future__ import annotations

import datetime as dt
from typing import Protocol


class ValidityRange(Protocol):
    valid_from: dt.date
    valid_to: dt.date | None


def season_bounds(season_year: int) -> tuple[dt.date, dt.date]:
    year = int(season_year)
    return dt.date(year, 1, 1), dt.date(year, 12, 31)


def overlaps_season(item: ValidityRange, season_year: int) -> bool:
    season_start, season_end = season_bounds(season_year)
    return item.valid_from <= season_end and (item.valid_to is None or item.valid_to >= season_start)


def planting_active_in_year(planting: ValidityRange, season_year: int) -> bool:
    return overlaps_season(planting, season_year)


def section_active_in_year(section, season_year: int) -> bool:
    planting = getattr(section, "planting", None)
    return overlaps_season(section, season_year) and (
        planting is None or planting_active_in_year(planting, season_year)
    )


def active_sections_for_year(planting, season_year: int) -> list:
    if not planting_active_in_year(planting, season_year):
        return []
    return [
        section
        for section in planting.sections
        if section_active_in_year(section, season_year)
    ]


def active_plantings_for_year(field, season_year: int) -> list:
    return [
        planting
        for planting in field.plantings
        if planting_active_in_year(planting, season_year)
    ]


def field_active_in_year(field, season_year: int) -> bool:
    return any(active_plantings_for_year(field, season_year))
