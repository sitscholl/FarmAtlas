from __future__ import annotations

import argparse
from difflib import get_close_matches
from pathlib import Path
import sys

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.database import models
from src.database.db import Database
from src.database.settings import get_database_url
from src.runtime import load_config_file


def _section_lookup(db: Database) -> tuple[dict[int, str], dict[str, int]]:
    with db.session_scope() as session:
        sections = [
            (section.id, section.name)
            for field in db.fields.list_all(session)
            for planting in field.plantings
            for section in planting.sections
        ]
    return dict(sections), {name.lower(): section_id for section_id, name in sections}


def _upsert_alias(
    db: Database,
    *,
    source: str,
    external_section_name: str,
    section_id: int,
) -> None:
    with db.session_scope() as session:
        section = session.get(models.Section, section_id)
        if section is None:
            raise ValueError(f"No section with id {section_id} found for alias {external_section_name!r}")

        alias = (
            session.query(models.TreatmentSectionAlias)
            .filter(
                models.TreatmentSectionAlias.source == source,
                models.TreatmentSectionAlias.external_section_name == external_section_name,
            )
            .one_or_none()
        )
        if alias is None:
            alias = models.TreatmentSectionAlias(
                source=source,
                external_section_name=external_section_name,
                section_id=section_id,
            )
            session.add(alias)
        else:
            alias.section_id = section_id

        db.treatments.resolve_events_for_alias(
            session,
            source=source,
            external_section_name=external_section_name,
            section_id=section_id,
        )


def apply_alias_map(db: Database, *, source: str, alias_map_path: Path) -> int:
    section_names_by_id, section_ids_by_name = _section_lookup(db)
    frame = pd.read_csv(alias_map_path)
    if "external_section_name" not in frame.columns:
        raise ValueError("Alias map must contain an external_section_name column")
    if "section_id" not in frame.columns and "section_name" not in frame.columns:
        raise ValueError("Alias map must contain either section_id or section_name")

    applied = 0
    for _, row in frame.iterrows():
        external_section_name = str(row["external_section_name"]).strip()
        if not external_section_name:
            continue

        section_id = None
        if "section_id" in frame.columns and not pd.isna(row.get("section_id")):
            section_id = int(row["section_id"])
            if section_id not in section_names_by_id:
                raise ValueError(f"No section with id {section_id} found")
        elif "section_name" in frame.columns and not pd.isna(row.get("section_name")):
            section_name = str(row["section_name"]).strip()
            section_id = section_ids_by_name.get(section_name.lower())
            if section_id is None:
                raise ValueError(f"No section named {section_name!r} found")

        if section_id is None:
            continue

        _upsert_alias(
            db,
            source=source,
            external_section_name=external_section_name,
            section_id=section_id,
        )
        applied += 1

    return applied


def write_unresolved_template(
    db: Database,
    *,
    source: str,
    season_year: int,
    output_path: Path,
) -> int:
    section_names_by_id, _ = _section_lookup(db)
    section_names = list(section_names_by_id.values())

    with db.session_scope() as session:
        unresolved = db.treatments.unresolved_external_section_names(
            session,
            source=source,
            season_year=season_year,
        )

    rows = []
    for external_name in unresolved:
        suggestions = get_close_matches(external_name, section_names, n=3, cutoff=0.25)
        rows.append(
            {
                "external_section_name": external_name,
                "section_name": suggestions[0] if suggestions else "",
                "section_id": next(
                    (
                        section_id
                        for section_id, section_name in section_names_by_id.items()
                        if suggestions and section_name == suggestions[0]
                    ),
                    "",
                ),
                "suggestions": " | ".join(suggestions),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legal treatment CSV rows into the configured FarmAtlas DB.")
    parser.add_argument("--csv", type=Path, default=ROOT_DIR / "bericht.csv")
    parser.add_argument("--season-year", type=int, required=True)
    parser.add_argument("--source", default="legal_export")
    parser.add_argument("--config", type=Path, default=BACKEND_DIR / "config" / "config.yaml")
    parser.add_argument("--alias-map", type=Path, default=None)
    parser.add_argument("--write-unresolved-template", type=Path, default=None)
    args = parser.parse_args()

    config = load_config_file(args.config)
    db = Database(get_database_url(config))
    try:
        if args.alias_map is not None:
            alias_count = apply_alias_map(db, source=args.source, alias_map_path=args.alias_map)
            print(f"Applied {alias_count} section alias(es) from {args.alias_map}")

        summary = db.treatment_import_service.import_full_season_csv(
            csv_text=args.csv.read_text(encoding="utf-8-sig"),
            season_year=args.season_year,
            source=args.source,
        )
        print(
            f"Imported {summary.row_count} treatment row(s) for {summary.source}/{summary.season_year}; "
            f"unresolved={summary.unresolved_count}"
        )

        if args.write_unresolved_template is not None:
            unresolved_count = write_unresolved_template(
                db,
                source=args.source,
                season_year=args.season_year,
                output_path=args.write_unresolved_template,
            )
            print(f"Wrote {unresolved_count} unresolved alias row(s) to {args.write_unresolved_template}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
