##Run with:
#uv run python scripts\import_yearly_stats.py
##

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.database import models
from src.database.db import Database
from src.database.settings import get_database_url
from src.runtime import load_config_file


REQUIRED_COLUMNS = {
    "season_year",
    "field_name",
    "planting_name",
    "thinning_hours",
    "harvest_hours",
    "filled_boxes",
    "yield_kg",
    "revenue",
}


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _required_text(row: dict[str, str], key: str) -> str:
    value = _optional_text(row.get(key))
    if value is None:
        raise ValueError(f"Missing required value for '{key}'")
    return value


def _required_int(row: dict[str, str], key: str) -> int:
    value = _required_text(row, key)
    return int(float(value.replace(",", ".")))


def _optional_float(value: str | None) -> float | None:
    text = _optional_text(value)
    if text is None:
        return None
    return float(text.replace(",", "."))


def _load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row found in {csv_path}")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                "Missing required CSV column(s): "
                f"{', '.join(sorted(missing_columns))}. "
                "Rename the CSV headers before importing."
            )

        return list(reader)


def _season_overlaps_planting(planting: models.Planting, season_year: int) -> bool:
    season_start = dt.date(season_year, 1, 1)
    season_end = dt.date(season_year, 12, 31)
    return planting.valid_from <= season_end and (planting.valid_to is None or planting.valid_to >= season_start)


def _find_planting(
    db: Database,
    *,
    field_name: str,
    planting_name: str,
    season_year: int,
) -> models.Planting:
    with db.session_scope() as session:
        candidates = (
            session.query(models.Planting)
            .join(models.Field, models.Planting.field_id == models.Field.id)
            .join(models.Variety, models.Planting.variety_id == models.Variety.id)
            .filter(func.lower(models.Field.name) == field_name.lower())
            .filter(func.lower(models.Variety.name) == planting_name.lower())
            .order_by(models.Planting.valid_from, models.Planting.id)
            .all()
        )

        if not candidates:
            raise ValueError(
                f"No planting found for field_name={field_name!r}, "
                f"planting_name={planting_name!r}"
            )

        matching_season = [
            planting
            for planting in candidates
            if _season_overlaps_planting(planting, season_year)
        ]
        if len(matching_season) == 1:
            return matching_season[0]

        if len(candidates) == 1:
            return candidates[0]

        candidate_descriptions = ", ".join(
            f"id={planting.id} valid_from={planting.valid_from} valid_to={planting.valid_to or ''}"
            for planting in candidates
        )
        raise ValueError(
            f"Ambiguous planting for field_name={field_name!r}, "
            f"planting_name={planting_name!r}, season_year={season_year}. "
            f"Candidates: {candidate_descriptions}"
        )


def _build_payload(row: dict[str, str], planting_id: int) -> dict[str, Any]:
    return {
        "season_year": _required_int(row, "season_year"),
        "planting_id": planting_id,
        "thinning_hours": _optional_float(row.get("thinning_hours")),
        "harvest_hours": _optional_float(row.get("harvest_hours")),
        "filled_boxes": _optional_float(row.get("filled_boxes")),
        "yield_kg": _optional_float(row.get("yield_kg")),
        "revenue": _optional_float(row.get("revenue")),
        "notes": _optional_text(row.get("notes")),
    }


def import_yearly_stats(db: Database, csv_path: Path) -> tuple[int, int]:
    rows = _load_csv_rows(csv_path)
    imported = 0
    failed = 0

    for row_number, row in enumerate(rows, start=2):
        try:
            season_year = _required_int(row, "season_year")
            field_name = _required_text(row, "field_name")
            planting_name = _required_text(row, "planting_name")
            planting = _find_planting(
                db,
                field_name=field_name,
                planting_name=planting_name,
                season_year=season_year,
            )

            with db.session_scope() as session:
                existing = (
                    session.query(models.YearlyStats)
                    .filter(
                        models.YearlyStats.planting_id == planting.id,
                        models.YearlyStats.season_year == season_year,
                    )
                    .one_or_none()
                )
                if existing is not None:
                    raise ValueError(
                        f"Yearly stats already exist for planting_id={planting.id}, "
                        f"season_year={season_year}"
                    )

                db.yearly_stats.create(session, **_build_payload(row, planting.id))
            imported += 1
        except Exception as exc:
            failed += 1
            print(f"WARNING row {row_number}: {exc}")

    return imported, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Import planting-level yearly stats into the configured FarmAtlas DB.")
    parser.add_argument("--csv", type=Path, default=ROOT_DIR / "yearly_stats.csv")
    parser.add_argument("--config", type=Path, default=BACKEND_DIR / "config" / "config.yaml")
    args = parser.parse_args()

    config = load_config_file(args.config)
    db = Database(get_database_url(config))
    try:
        imported, failed = import_yearly_stats(db, args.csv)
        print(f"Imported {imported} yearly stats row(s) from {args.csv}; failed={failed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
