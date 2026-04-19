from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_VARIETIES_CSV_PATH = ROOT_DIR / "db_varieties.csv"
DEFAULT_FIELDS_CSV_PATH = ROOT_DIR / "db_fields.csv"
DEFAULT_PLANTINGS_CSV_PATH = ROOT_DIR / "db_plantings.csv"
DEFAULT_SECTIONS_CSV_PATH = ROOT_DIR / "db_sections.csv"
DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
DEFAULT_FIELD_ELEVATION = 0.0


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _required_text(row: dict[str, str], key: str) -> str:
    value = _optional_text(row.get(key))
    if value is None:
        raise ValueError(f"Missing required column '{key}'")
    return value


def _required_text_any(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = _optional_text(row.get(key))
        if value is not None:
            return value
    raise ValueError(f"Missing required column; expected one of {', '.join(keys)}")


def _optional_float(value: str | None) -> float | None:
    text = _optional_text(value)
    if text is None:
        return None
    return float(text.replace(",", "."))


def _required_float(row: dict[str, str], key: str) -> float:
    value = _optional_float(row.get(key))
    if value is None:
        raise ValueError(f"Missing required numeric column '{key}'")
    return value


def _optional_int(value: str | None) -> int | None:
    text = _optional_text(value)
    if text is None:
        return None
    return int(float(text.replace(",", ".")))


def _required_int(row: dict[str, str], key: str) -> int:
    value = _optional_int(row.get(key))
    if value is None:
        raise ValueError(f"Missing required integer column '{key}'")
    return value


def _optional_bool(value: str | None) -> bool | None:
    text = _optional_text(value)
    if text is None:
        return None

    normalized = text.lower()
    if normalized in {"true", "1", "yes", "y", "ja"}:
        return True
    if normalized in {"false", "0", "no", "n", "nein"}:
        return False
    raise ValueError(f"Unsupported boolean value '{text}'")


def _optional_iso_date(value: str | None) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    return dt.date.fromisoformat(text).isoformat()


def _iso_date_from_year(year: int) -> str:
    return dt.date(int(year), 1, 1).isoformat()


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = None
        if body:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
        return exc.code, parsed


def _load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No header row found in {csv_path}")
        return list(reader)


def _build_variety_payload(row: dict[str, str]) -> dict[str, Any]:
    return {
        "name": _required_text(row, "name"),
        "group": _required_text(row, "group"),
        "slope": _optional_float(row.get("slope")),
        "intercept": _optional_float(row.get("intercept")),
        "kg_per_box": _optional_float(row.get("kg_per_box")),
        "nr_per_kg": _optional_float(row.get("nr_per_kg")),
        "specific_weight": _optional_float(row.get("specific_weight")),
    }


def _build_field_payload(
    row: dict[str, str],
    *,
    default_elevation: float,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    elevation = _optional_float(row.get("elevation"))
    if elevation is None:
        elevation = float(default_elevation)
        warnings.append(
            f"Field '{_required_text(row, 'name')}' has no elevation in db_fields.csv. "
            f"Using default elevation {default_elevation}."
        )

    payload = {
        "group": _required_text_any(row, "group", "Group"),
        "name": _required_text(row, "name"),
        "reference_provider": _required_text(row, "reference_provider"),
        "reference_station": _required_text(row, "reference_station"),
        "elevation": elevation,
        "soil_type": _optional_text(row.get("soil_type")),
        "soil_weight": _optional_text(row.get("soil_weight")),
        "humus_pct": _optional_float(row.get("humus_pct")),
        "effective_root_depth_cm": _optional_float(row.get("effective_root_depth_cm")),
        "p_allowable": _optional_float(row.get("p_allowable")),
        "drip_distance": _optional_float(row.get("drip_distance")),
        "drip_discharge": _optional_float(row.get("drip_discharge")),
        "tree_strip_width": _optional_float(row.get("tree_strip_width")),
        "valve_open": True,
    }
    return payload, warnings


def _build_planting_payload(
    row: dict[str, str],
    *,
    field_id: int,
    inferred_valid_from: str,
) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "variety": _required_text_any(row, "variety_name", "variety"),
        "valid_from": _optional_iso_date(row.get("valid_from")) or inferred_valid_from,
        "valid_to": _optional_iso_date(row.get("valid_to")),
    }


def _build_section_payload(
    row: dict[str, str],
    *,
    planting_id: int,
    area_multiplier: float,
    running_metre_multiplier: float,
) -> dict[str, Any]:
    planting_year = _required_int(row, "planting_year")
    running_metre = _optional_float(row.get("running_metre"))
    return {
        "planting_id": planting_id,
        "name": _required_text(row, "name"),
        "planting_year": planting_year,
        "area": _required_float(row, "area_ha") * area_multiplier,
        "tree_count": _optional_int(row.get("tree_count")),
        "tree_height": _optional_float(row.get("tree_height")),
        "row_distance": _optional_float(row.get("row_distance")),
        "tree_distance": _optional_float(row.get("tree_distance")),
        "running_metre": None if running_metre is None else running_metre * running_metre_multiplier,
        "herbicide_free": _optional_bool(row.get("herbicide_free")),
        "valid_from": _optional_iso_date(row.get("valid_from")) or _iso_date_from_year(planting_year),
        "valid_to": _optional_iso_date(row.get("valid_to")),
    }


def _list_json(api_base: str, resource: str) -> list[dict[str, Any]]:
    status, body = _request_json("GET", f"{api_base}{resource}")
    if status >= 400:
        raise RuntimeError(f"Failed to list {resource}: HTTP {status} - {body}")
    return list(body or [])


def _validate_csv_links(
    *,
    varieties_rows: list[dict[str, str]],
    fields_rows: list[dict[str, str]],
    plantings_rows: list[dict[str, str]],
    sections_rows: list[dict[str, str]],
) -> list[str]:
    issues: list[str] = []

    field_names = [_required_text(row, "name") for row in fields_rows]
    duplicate_field_names = sorted({name for name in field_names if field_names.count(name) > 1})
    if duplicate_field_names:
        issues.append(
            "Duplicate field names in db_fields.csv make planting/section links ambiguous: "
            + ", ".join(duplicate_field_names)
        )

    variety_names = {_required_text(row, "name") for row in varieties_rows}
    missing_planting_varieties = sorted(
        {
            _required_text_any(row, "variety_name", "variety")
            for row in plantings_rows
            if _required_text_any(row, "variety_name", "variety") not in variety_names
        }
    )
    if missing_planting_varieties:
        issues.append(
            "Plantings reference unknown varieties: " + ", ".join(missing_planting_varieties)
        )

    field_name_set = set(field_names)
    missing_planting_fields = sorted(
        {
            _required_text(row, "field_name")
            for row in plantings_rows
            if _required_text(row, "field_name") not in field_name_set
        }
    )
    if missing_planting_fields:
        issues.append(
            "Plantings reference unknown fields: " + ", ".join(missing_planting_fields)
        )

    planting_keys = {
        (
            _required_text(row, "field_name"),
            _required_text_any(row, "variety_name", "variety"),
        )
        for row in plantings_rows
    }
    duplicate_planting_keys = sorted(
        {
            f"{_required_text(row, 'field_name')} / {_required_text_any(row, 'variety_name', 'variety')}"
            for row in plantings_rows
            if sum(
                1
                for candidate in plantings_rows
                if _required_text(candidate, "field_name") == _required_text(row, "field_name")
                and _required_text_any(candidate, "variety_name", "variety") == _required_text_any(row, "variety_name", "variety")
            ) > 1
        }
    )
    if duplicate_planting_keys:
        issues.append(
            "Duplicate planting keys in db_plantings.csv are not supported by this importer: "
            + ", ".join(duplicate_planting_keys)
        )

    missing_section_fields = sorted(
        {
            _required_text(row, "field_name")
            for row in sections_rows
            if _required_text(row, "field_name") not in field_name_set
        }
    )
    if missing_section_fields:
        issues.append(
            "Sections reference unknown fields: " + ", ".join(missing_section_fields)
        )

    missing_section_plantings = sorted(
        {
            f"{_required_text(row, 'field_name')} / {_required_text_any(row, 'variety', 'variety_name')}"
            for row in sections_rows
            if (
                _required_text(row, "field_name"),
                _required_text_any(row, "variety", "variety_name"),
            )
            not in planting_keys
        }
    )
    if missing_section_plantings:
        issues.append(
            "Sections reference missing planting pairs (field_name + variety): "
            + ", ".join(missing_section_plantings)
        )

    return issues


def _ensure_varieties(
    rows: list[dict[str, str]],
    *,
    api_base: str,
    dry_run: bool,
) -> dict[str, dict[str, Any]]:
    existing = {
        str(item["name"]).strip(): item
        for item in _list_json(api_base, "/varieties")
        if isinstance(item, dict) and item.get("name")
    }

    for row in rows:
        payload = _build_variety_payload(row)
        variety_name = payload["name"]
        if variety_name in existing:
            continue

        if dry_run:
            print(f"[dry-run] Would create variety '{variety_name}'.")
            existing[variety_name] = payload
            continue

        status, body = _request_json("POST", f"{api_base}/varieties", payload)
        if status >= 400 and status != 409:
            raise RuntimeError(f"Failed to create variety '{variety_name}': HTTP {status} - {body}")
        print(f"Created variety '{variety_name}'.")

        refreshed = _list_json(api_base, "/varieties")
        existing = {
            str(item["name"]).strip(): item
            for item in refreshed
            if isinstance(item, dict) and item.get("name")
        }

    return existing


def _ensure_fields(
    rows: list[dict[str, str]],
    *,
    api_base: str,
    dry_run: bool,
    default_elevation: float,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    warnings: list[str] = []
    existing_fields = _list_json(api_base, "/fields")
    fields_by_name = {
        str(item["name"]).strip(): item
        for item in existing_fields
        if isinstance(item, dict) and item.get("name")
    }

    for row in rows:
        payload, row_warnings = _build_field_payload(row, default_elevation=default_elevation)
        warnings.extend(row_warnings)
        field_name = payload["name"]

        if field_name in fields_by_name:
            continue

        if dry_run:
            print(f"[dry-run] Would create field '{field_name}'.")
            fields_by_name[field_name] = {"id": None, **payload}
            continue

        status, body = _request_json("POST", f"{api_base}/fields", payload)
        if status >= 400 and status != 409:
            raise RuntimeError(f"Failed to create field '{field_name}': HTTP {status} - {body}")
        print(f"Created field '{field_name}'.")

        refreshed = _list_json(api_base, "/fields")
        fields_by_name = {
            str(item["name"]).strip(): item
            for item in refreshed
            if isinstance(item, dict) and item.get("name")
        }

    return fields_by_name, warnings


def _build_planting_valid_from_map(sections_rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    valid_from_by_key: dict[tuple[str, str], str] = {}
    for row in sections_rows:
        key = (
            _required_text(row, "field_name"),
            _required_text_any(row, "variety", "variety_name"),
        )
        inferred = _optional_iso_date(row.get("valid_from")) or _iso_date_from_year(_required_int(row, "planting_year"))
        current = valid_from_by_key.get(key)
        if current is None or inferred < current:
            valid_from_by_key[key] = inferred
    return valid_from_by_key


def _ensure_plantings(
    rows: list[dict[str, str]],
    *,
    sections_rows: list[dict[str, str]],
    fields_by_name: dict[str, dict[str, Any]],
    api_base: str,
    dry_run: bool,
) -> dict[tuple[str, str], dict[str, Any]]:
    planting_valid_from_map = _build_planting_valid_from_map(sections_rows)
    plantings_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for field_name, field in fields_by_name.items():
        field_id = field.get("id")
        if field_id is None:
            continue
        for planting in _list_json(api_base, f"/fields/{field_id}/plantings"):
            key = (field_name, str(planting["variety"]).strip())
            plantings_by_key[key] = planting

    for row in rows:
        field_name = _required_text(row, "field_name")
        variety_name = _required_text_any(row, "variety_name", "variety")
        key = (field_name, variety_name)
        if key in plantings_by_key:
            continue

        field = fields_by_name[field_name]
        field_id = field.get("id")
        if field_id is None:
            print(f"[dry-run] Would create planting '{field_name}' / '{variety_name}'.")
            plantings_by_key[key] = {"id": None, "field_id": None, "variety": variety_name}
            continue

        inferred_valid_from = planting_valid_from_map.get(key)
        if inferred_valid_from is None:
            raise RuntimeError(
                f"Cannot infer valid_from for planting '{field_name}' / '{variety_name}'. "
                f"Add a valid_from column to db_plantings.csv or matching sections to db_sections.csv."
            )

        payload = _build_planting_payload(
            row,
            field_id=int(field_id),
            inferred_valid_from=inferred_valid_from,
        )

        if dry_run:
            print(
                f"[dry-run] Would create planting '{field_name}' / '{variety_name}' "
                f"(valid_from={payload['valid_from']})."
            )
            plantings_by_key[key] = {"id": None, **payload}
            continue

        status, body = _request_json("POST", f"{api_base}/plantings", payload)
        if status >= 400 and status != 409:
            raise RuntimeError(
                f"Failed to create planting '{field_name}' / '{variety_name}': HTTP {status} - {body}"
            )
        print(
            f"Created planting '{field_name}' / '{variety_name}' "
            f"(valid_from={payload['valid_from']})."
        )

        refreshed = _list_json(api_base, f"/fields/{field_id}/plantings")
        for planting in refreshed:
            planting_key = (field_name, str(planting["variety"]).strip())
            plantings_by_key[planting_key] = planting

    return plantings_by_key


def _ensure_sections(
    rows: list[dict[str, str]],
    *,
    plantings_by_key: dict[tuple[str, str], dict[str, Any]],
    api_base: str,
    dry_run: bool,
    area_unit: str,
    running_metre_unit: str,
) -> None:
    area_multiplier = 1.0 if area_unit == "sqm" else 10000.0
    running_metre_multiplier = 1000.0 if running_metre_unit == "km" else 1.0

    existing_sections_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (field_name, variety_name), planting in plantings_by_key.items():
        planting_id = planting.get("id")
        if planting_id is None:
            continue
        for section in _list_json(api_base, f"/plantings/{planting_id}/sections"):
            existing_sections_by_key[(field_name, variety_name, str(section["name"]).strip())] = section

    for row in rows:
        field_name = _required_text(row, "field_name")
        variety_name = _required_text_any(row, "variety", "variety_name")
        section_name = _required_text(row, "name")
        key = (field_name, variety_name, section_name)
        if key in existing_sections_by_key:
            continue

        planting = plantings_by_key[(field_name, variety_name)]
        planting_id = planting.get("id")
        payload = _build_section_payload(
            row,
            planting_id=0 if planting_id is None else int(planting_id),
            area_multiplier=area_multiplier,
            running_metre_multiplier=running_metre_multiplier,
        )

        if dry_run:
            print(
                f"[dry-run] Would create section '{section_name}' under '{field_name}' / '{variety_name}' "
                f"(valid_from={payload['valid_from']})."
            )
            existing_sections_by_key[key] = {"id": None, **payload}
            continue

        status, body = _request_json("POST", f"{api_base}/sections", payload)
        if status >= 400 and status != 409:
            raise RuntimeError(
                f"Failed to create section '{section_name}' under '{field_name}' / '{variety_name}': "
                f"HTTP {status} - {body}"
            )
        print(
            f"Created section '{section_name}' under '{field_name}' / '{variety_name}' "
            f"(valid_from={payload['valid_from']})."
        )


def import_database(
    *,
    varieties_csv_path: Path,
    fields_csv_path: Path,
    plantings_csv_path: Path,
    sections_csv_path: Path,
    api_base: str,
    dry_run: bool,
    default_elevation: float,
    area_unit: str,
    running_metre_unit: str,
) -> int:
    varieties_rows = _load_csv_rows(varieties_csv_path)
    fields_rows = _load_csv_rows(fields_csv_path)
    plantings_rows = _load_csv_rows(plantings_csv_path)
    sections_rows = _load_csv_rows(sections_csv_path)

    issues = _validate_csv_links(
        varieties_rows=varieties_rows,
        fields_rows=fields_rows,
        plantings_rows=plantings_rows,
        sections_rows=sections_rows,
    )
    if issues:
        for issue in issues:
            print(f"CSV validation error: {issue}")
        return 1

    _ensure_varieties(varieties_rows, api_base=api_base, dry_run=dry_run)
    fields_by_name, warnings = _ensure_fields(
        fields_rows,
        api_base=api_base,
        dry_run=dry_run,
        default_elevation=default_elevation,
    )
    for warning in warnings:
        print(f"Warning: {warning}")

    plantings_by_key = _ensure_plantings(
        plantings_rows,
        sections_rows=sections_rows,
        fields_by_name=fields_by_name,
        api_base=api_base,
        dry_run=dry_run,
    )
    _ensure_sections(
        sections_rows,
        plantings_by_key=plantings_by_key,
        api_base=api_base,
        dry_run=dry_run,
        area_unit=area_unit,
        running_metre_unit=running_metre_unit,
    )

    print(
        "Import finished "
        f"(varieties={varieties_csv_path}, fields={fields_csv_path}, "
        f"plantings={plantings_csv_path}, sections={sections_csv_path}, api={api_base})."
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import varieties, fields, plantings, and sections from the refactored CSV files.",
    )
    parser.add_argument(
        "--varieties-csv",
        dest="varieties_csv_path",
        type=Path,
        default=DEFAULT_VARIETIES_CSV_PATH,
        help=f"Path to db_varieties.csv. Default: {DEFAULT_VARIETIES_CSV_PATH}",
    )
    parser.add_argument(
        "--fields-csv",
        dest="fields_csv_path",
        type=Path,
        default=DEFAULT_FIELDS_CSV_PATH,
        help=f"Path to db_fields.csv. Default: {DEFAULT_FIELDS_CSV_PATH}",
    )
    parser.add_argument(
        "--plantings-csv",
        dest="plantings_csv_path",
        type=Path,
        default=DEFAULT_PLANTINGS_CSV_PATH,
        help=f"Path to db_plantings.csv. Default: {DEFAULT_PLANTINGS_CSV_PATH}",
    )
    parser.add_argument(
        "--sections-csv",
        dest="sections_csv_path",
        type=Path,
        default=DEFAULT_SECTIONS_CSV_PATH,
        help=f"Path to db_sections.csv. Default: {DEFAULT_SECTIONS_CSV_PATH}",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"Base API URL without trailing slash. Default: {DEFAULT_API_BASE}",
    )
    parser.add_argument(
        "--default-elevation",
        type=float,
        default=DEFAULT_FIELD_ELEVATION,
        help=(
            "Fallback elevation used when db_fields.csv has no elevation value. "
            f"Default: {DEFAULT_FIELD_ELEVATION}"
        ),
    )
    parser.add_argument(
        "--area-unit",
        choices=("sqm", "ha"),
        default="sqm",
        help=(
            "Unit used by db_sections.csv area_ha values. "
            "'sqm' keeps values as m^2, 'ha' converts hectares to m^2. Default: sqm"
        ),
    )
    parser.add_argument(
        "--running-metre-unit",
        choices=("km", "m"),
        default="km",
        help=(
            "Unit used by db_sections.csv running_metre values. "
            "'km' converts to metres, 'm' keeps values as metres. Default: km"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print what would be created without POSTing new rows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return import_database(
        varieties_csv_path=args.varieties_csv_path.resolve(),
        fields_csv_path=args.fields_csv_path.resolve(),
        plantings_csv_path=args.plantings_csv_path.resolve(),
        sections_csv_path=args.sections_csv_path.resolve(),
        api_base=args.api_base.rstrip("/"),
        dry_run=bool(args.dry_run),
        default_elevation=float(args.default_elevation),
        area_unit=str(args.area_unit),
        running_metre_unit=str(args.running_metre_unit),
    )


if __name__ == "__main__":
    sys.exit(main())
