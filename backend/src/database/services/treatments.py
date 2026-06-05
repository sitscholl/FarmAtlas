import datetime
import hashlib
import math
from io import StringIO
from typing import Any

import pandas as pd

from ..core import DatabaseCore
from ..repositories import TreatmentRepository


CSV_COLUMNS = {
    "date": "Datum",
    "external_section_name": "Anlage",
    "product_name": "Mittel",
    "dose_per_hl": "Dosis /hl 1x",
    "hl": "hl 1x",
    "reason": "Grund",
    "cost": "Kosten",
}


def _normalize_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _parse_optional_float(value: Any) -> float | None:
    text = _normalize_text(value)
    if text == "":
        return None
    normalized = text.replace("€", "").replace("EUR", "").strip()
    normalized = normalized.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValueError(f"Could not parse numeric value {value!r}") from exc


def _row_hash(values: dict[str, Any]) -> str:
    parts = [
        str(values.get("date", "")),
        str(values.get("external_section_name", "")),
        str(values.get("product_name", "")),
        str(values.get("reason", "")),
        str(values.get("dose_per_hl", "")),
        str(values.get("hl", "")),
        str(values.get("cost", "")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


class TreatmentImportService:
    def __init__(self, core: DatabaseCore, treatments: TreatmentRepository) -> None:
        self._core = core
        self._treatments = treatments

    def _parse_csv(self, csv_text: str, *, source: str, season_year: int) -> list[dict[str, Any]]:
        frame = pd.read_csv(StringIO(csv_text))
        missing_columns = [column for column in CSV_COLUMNS.values() if column not in frame.columns]
        if missing_columns:
            raise ValueError(f"Treatment CSV is missing required columns: {', '.join(missing_columns)}")

        parsed_rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            date_value = pd.to_datetime(row[CSV_COLUMNS["date"]], dayfirst=True, errors="raise").date()
            external_section_name = _normalize_text(row[CSV_COLUMNS["external_section_name"]])
            product_name = _normalize_text(row[CSV_COLUMNS["product_name"]])
            if external_section_name == "":
                raise ValueError("Treatment CSV contains an empty Anlage value")
            if product_name == "":
                raise ValueError("Treatment CSV contains an empty Mittel value")

            values = {
                "source": source,
                "season_year": int(season_year),
                "date": date_value,
                "external_section_name": external_section_name,
                "product_name": product_name,
                "reason": _normalize_text(row[CSV_COLUMNS["reason"]]) or None,
                "dose_per_hl": _parse_optional_float(row[CSV_COLUMNS["dose_per_hl"]]),
                "hl": _parse_optional_float(row[CSV_COLUMNS["hl"]]),
                "cost": _parse_optional_float(row[CSV_COLUMNS["cost"]]),
            }
            values["row_hash"] = _row_hash(values)
            parsed_rows.append(values)
        return parsed_rows

    def import_full_season_csv(
        self,
        *,
        csv_text: str,
        season_year: int,
        source: str = "legal_export",
    ):
        normalized_source = source.strip() or "legal_export"
        records = self._parse_csv(csv_text, source=normalized_source, season_year=season_year)

        with self._core.session_scope() as session:
            alias_map = self._treatments.get_alias_map(session, source=normalized_source)
            for record in records:
                section_id = alias_map.get(record["external_section_name"])
                record["section_id"] = section_id
                record["resolution_status"] = "resolved" if section_id is not None else "unresolved"

            inserted_count = self._treatments.replace_season_events(
                session,
                source=normalized_source,
                season_year=season_year,
                records=records,
            )
            unresolved_count = sum(1 for record in records if record["resolution_status"] == "unresolved")
            summary = self._treatments.upsert_import_summary(
                session,
                source=normalized_source,
                season_year=season_year,
                imported_at=datetime.datetime.now(datetime.UTC),
                row_count=inserted_count,
                unresolved_count=unresolved_count,
            )
            return summary

    def create_alias(self, *, source: str, external_section_name: str, section_id: int):
        normalized_source = source.strip() or "legal_export"
        normalized_name = external_section_name.strip()
        if not normalized_name:
            raise ValueError("external_section_name must not be empty")
        with self._core.session_scope() as session:
            alias = self._treatments.create_alias(
                session,
                source=normalized_source,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            self._treatments.resolve_events_for_alias(
                session,
                source=normalized_source,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            return alias

    def update_alias(self, alias_id: int, *, source: str, external_section_name: str, section_id: int):
        normalized_source = source.strip() or "legal_export"
        normalized_name = external_section_name.strip()
        if not normalized_name:
            raise ValueError("external_section_name must not be empty")
        with self._core.session_scope() as session:
            old_alias = self._treatments.get_alias_by_id(session, alias_id)
            if old_alias is None:
                raise ValueError(f"Could not find any treatment section alias with id {alias_id}")
            old_source = old_alias.source
            old_name = old_alias.external_section_name
            alias = self._treatments.update_alias(
                session,
                alias_id,
                source=normalized_source,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            self._treatments.resolve_events_for_alias(
                session,
                source=old_source,
                external_section_name=old_name,
                section_id=None,
            )
            self._treatments.resolve_events_for_alias(
                session,
                source=normalized_source,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            return alias

    def delete_alias(self, alias_id: int) -> bool:
        with self._core.session_scope() as session:
            alias = self._treatments.get_alias_by_id(session, alias_id)
            if alias is None:
                return False
            source = alias.source
            external_section_name = alias.external_section_name
            deleted = self._treatments.delete_alias(session, alias_id)
            if deleted:
                self._treatments.resolve_events_for_alias(
                    session,
                    source=source,
                    external_section_name=external_section_name,
                    section_id=None,
                )
            return deleted
