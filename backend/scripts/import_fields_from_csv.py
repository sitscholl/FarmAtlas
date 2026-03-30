from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = ROOT_DIR / "fields_table.csv"
DEFAULT_API_BASE = "http://127.0.0.1:8000/api"
DEFAULT_VARIETY_GROUP = "unknown"


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


def _build_field_payload(
    row: dict[str, str],
    *,
    area_multiplier: float,
    running_metre_multiplier: float,
) -> dict[str, Any]:
    area_value = _required_float(row, "area_ha") * area_multiplier
    running_metre_value = _optional_float(row.get("running_metre"))

    payload = {
        "name": _required_text(row, "name"),
        "section": _optional_text(row.get("section")),
        "variety": _required_text(row, "variety"),
        "planting_year": _required_int(row, "planting_year"),
        "tree_count": _optional_int(row.get("tree_count")),
        "tree_height": _optional_float(row.get("tree_height")),
        "row_distance": _optional_float(row.get("row_distance")),
        "tree_distance": _optional_float(row.get("tree_distance")),
        "running_metre": None if running_metre_value is None else running_metre_value * running_metre_multiplier,
        "herbicide_free": _optional_bool(row.get("herbicide_free")),
        "active": True,
        "reference_provider": _required_text(row, "reference_provider"),
        "reference_station": _required_text(row, "reference_station"),
        "soil_type": _optional_text(row.get("soil_type")),
        "soil_weight": _optional_text(row.get("soil_weight")),
        "humus_pct": _optional_float(row.get("humus_pct")),
        "area_ha": area_value,
        "effective_root_depth_cm": _optional_float(row.get("effective_root_depth_cm")),
        "p_allowable": _optional_float(row.get("p_allowable")),
    }
    return payload


def _ensure_varieties(
    rows: list[dict[str, str]],
    *,
    api_base: str,
    create_missing: bool,
    default_group: str,
    dry_run: bool,
) -> None:
    status, body = _request_json("GET", f"{api_base}/varieties")
    if status >= 400:
        raise RuntimeError(f"Failed to list varieties: HTTP {status} - {body}")

    existing_names = {
        str(item["name"]).strip()
        for item in (body or [])
        if isinstance(item, dict) and item.get("name")
    }
    missing_names = sorted(
        {
            _required_text(row, "variety")
            for row in rows
            if _required_text(row, "variety") not in existing_names
        }
    )

    if not missing_names:
        print("No missing varieties detected.")
        return

    if not create_missing:
        raise RuntimeError(
            "Missing varieties in database: "
            + ", ".join(missing_names)
            + ". Re-run with --create-missing-varieties."
        )

    for variety_name in missing_names:
        payload = {
            "name": variety_name,
            "group": default_group,
        }
        if dry_run:
            print(f"[dry-run] Would create variety '{variety_name}' with group '{default_group}'.")
            continue

        status, body = _request_json("POST", f"{api_base}/varieties", payload)
        if status >= 400 and status != 409:
            raise RuntimeError(f"Failed to create variety '{variety_name}': HTTP {status} - {body}")
        print(f"Created variety '{variety_name}'.")


def import_fields(
    *,
    csv_path: Path,
    api_base: str,
    area_unit: str,
    running_metre_unit: str,
    create_missing_varieties: bool,
    default_variety_group: str,
    dry_run: bool,
) -> int:
    rows = _load_csv_rows(csv_path)
    if not rows:
        print(f"No rows found in {csv_path}.")
        return 0

    area_multiplier = 1.0 if area_unit == "ha" else 0.0001
    running_metre_multiplier = 1.0 if running_metre_unit == "m" else 1000.0

    _ensure_varieties(
        rows,
        api_base=api_base,
        create_missing=create_missing_varieties,
        default_group=default_variety_group,
        dry_run=dry_run,
    )

    created = 0
    skipped = 0
    failed = 0
    for index, row in enumerate(rows, start=1):
        try:
            payload = _build_field_payload(
                row,
                area_multiplier=area_multiplier,
                running_metre_multiplier=running_metre_multiplier,
            )
        except Exception as exc:
            failed += 1
            print(f"[row {index}] Invalid CSV data: {exc}")
            continue

        if dry_run:
            print(f"[dry-run] Would create field '{payload['name']}' ({payload['variety']}).")
            created += 1
            continue

        status, body = _request_json("POST", f"{api_base}/fields", payload)
        if 200 <= status < 300:
            created += 1
            print(f"[row {index}] Created field '{payload['name']}' ({payload['variety']}).")
            continue

        if status == 409:
            skipped += 1
            print(f"[row {index}] Skipped existing field '{payload['name']}' ({payload['variety']}).")
            continue

        failed += 1
        print(f"[row {index}] Failed to create field '{payload['name']}': HTTP {status} - {body}")

    print(
        f"Import finished. created={created}, skipped={skipped}, failed={failed}, "
        f"csv={csv_path}, api={api_base}"
    )
    return 0 if failed == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import fields from fields_table.csv by calling the backend /api/fields endpoint.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"Path to the CSV file. Default: {DEFAULT_CSV_PATH}",
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"Base API URL without trailing slash. Default: {DEFAULT_API_BASE}",
    )
    parser.add_argument(
        "--area-unit",
        choices=("sqm", "ha"),
        default="sqm",
        help="Unit of the CSV area_ha column. 'sqm' converts to hectares before POSTing. Default: sqm",
    )
    parser.add_argument(
        "--running-metre-unit",
        choices=("km", "m"),
        default="km",
        help="Unit of the CSV running_metre column. 'km' converts to metres before POSTing. Default: km",
    )
    parser.add_argument(
        "--create-missing-varieties",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create missing varieties through /api/varieties before importing fields. Default: true",
    )
    parser.add_argument(
        "--default-variety-group",
        default=DEFAULT_VARIETY_GROUP,
        help=f"Group used when auto-creating missing varieties. Default: {DEFAULT_VARIETY_GROUP}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print what would be created without calling the API.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return import_fields(
        csv_path=args.csv_path.resolve(),
        api_base=args.api_base.rstrip("/"),
        area_unit=args.area_unit,
        running_metre_unit=args.running_metre_unit,
        create_missing_varieties=bool(args.create_missing_varieties),
        default_variety_group=str(args.default_variety_group),
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    sys.exit(main())
