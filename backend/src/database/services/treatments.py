import datetime
import hashlib
import math
import re
from io import StringIO
from collections.abc import Iterable
from typing import Any

import pandas as pd

from .. import models
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


def _normalize_external_section_name(value: Any) -> str:
    return re.sub(r"\s+", " ", _normalize_text(value)).strip().lower()


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

    @staticmethod
    def _resolve_events_for_normalized_alias(
        session,
        *,
        source: str | None = None,
        external_section_name: str,
        section_id: int | None,
    ) -> int:
        normalized_name = _normalize_external_section_name(external_section_name)
        resolved_count = 0
        query = session.query(models.TreatmentEvent)
        if source is not None:
            query = query.filter(models.TreatmentEvent.source == source)
        events = query.all()
        for event in events:
            if _normalize_external_section_name(event.external_section_name) != normalized_name:
                continue
            event.external_section_name = normalized_name
            event.section_id = section_id
            event.resolution_status = "resolved" if section_id is not None else "unresolved"
            resolved_count += 1
        return resolved_count

    def _parse_frame(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        missing_columns = [column for column in CSV_COLUMNS.values() if column not in frame.columns]
        if missing_columns:
            raise ValueError(f"Treatment export is missing required columns: {', '.join(missing_columns)}")

        parsed_rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            date_value = pd.to_datetime(row[CSV_COLUMNS["date"]], dayfirst=True, errors="raise").date()
            external_section_name = _normalize_external_section_name(row[CSV_COLUMNS["external_section_name"]])
            product_name = _normalize_text(row[CSV_COLUMNS["product_name"]])
            if external_section_name == "":
                raise ValueError("Treatment CSV contains an empty Anlage value")
            if product_name == "":
                raise ValueError("Treatment CSV contains an empty Mittel value")

            values = {
                "date": date_value,
                "external_section_name": external_section_name,
                "product_name": product_name,
                "reason": _normalize_text(row[CSV_COLUMNS["reason"]]) or None,
                "dose_per_hl": _parse_optional_float(row[CSV_COLUMNS["dose_per_hl"]]),
                "hl": _parse_optional_float(row[CSV_COLUMNS["hl"]]),
                "cost": _parse_optional_float(row[CSV_COLUMNS["cost"]]),
            }
            parsed_rows.append(values)
        return parsed_rows

    def _parse_csv(self, csv_text: str) -> list[dict[str, Any]]:
        return self._parse_frame(pd.read_csv(StringIO(csv_text)))

    def _prepare_records(
        self,
        records: Iterable[dict[str, Any]],
        *,
        source: str,
        season_year: int,
    ) -> list[dict[str, Any]]:
        prepared_rows: list[dict[str, Any]] = []
        for record in records:
            values = dict(record)
            values["source"] = source
            values["season_year"] = int(season_year)
            values["external_section_name"] = _normalize_external_section_name(
                values.get("external_section_name"),
            )
            values["product_name"] = _normalize_text(values.get("product_name"))
            if not values.get("external_section_name"):
                raise ValueError("Treatment export contains an empty Anlage value")
            if not values.get("product_name"):
                raise ValueError("Treatment export contains an empty Mittel value")
            values["row_hash"] = values.get("row_hash") or _row_hash(values)
            prepared_rows.append(values)
        return prepared_rows

    def import_full_season_records(
        self,
        *,
        records: Iterable[dict[str, Any]],
        season_year: int,
        source: str = "legal_export",
    ):
        normalized_source = source.strip() or "legal_export"
        prepared_records = self._prepare_records(
            records,
            source=normalized_source,
            season_year=season_year,
        )

        with self._core.session_scope() as session:
            alias_map = {
                _normalize_external_section_name(alias.external_section_name): alias.section_id
                for alias in self._treatments.list_aliases(session, source=None)
            }
            for record in prepared_records:
                section_id = alias_map.get(record["external_section_name"])
                record["section_id"] = section_id
                record["resolution_status"] = "resolved" if section_id is not None else "unresolved"

            inserted_count = self._treatments.replace_season_events(
                session,
                source=normalized_source,
                season_year=season_year,
                records=prepared_records,
            )
            unresolved_count = sum(
                1 for record in prepared_records if record["resolution_status"] == "unresolved"
            )
            return self._treatments.upsert_import_summary(
                session,
                source=normalized_source,
                season_year=season_year,
                imported_at=datetime.datetime.now(datetime.UTC),
                row_count=inserted_count,
                unresolved_count=unresolved_count,
            )

    def import_full_season_dataframe(
        self,
        *,
        dataframe: pd.DataFrame,
        season_year: int,
        source: str = "legal_export",
    ):
        return self.import_full_season_records(
            records=self._parse_frame(dataframe),
            season_year=season_year,
            source=source,
        )

    def import_full_season_csv(
        self,
        *,
        csv_text: str,
        season_year: int,
        source: str = "legal_export",
    ):
        return self.import_full_season_records(
            records=self._parse_csv(csv_text),
            season_year=season_year,
            source=source,
        )

    def create_alias(self, *, source: str, external_section_name: str, section_id: int):
        normalized_source = source.strip() or "legal_export"
        normalized_name = _normalize_external_section_name(external_section_name)
        if not normalized_name:
            raise ValueError("external_section_name must not be empty")
        with self._core.session_scope() as session:
            existing_alias = next(
                (
                    alias
                    for alias in self._treatments.list_aliases(session, source=None)
                    if _normalize_external_section_name(alias.external_section_name) == normalized_name
                ),
                None,
            )
            if existing_alias is None:
                alias = self._treatments.create_alias(
                    session,
                    source=normalized_source,
                    external_section_name=normalized_name,
                    section_id=section_id,
                )
            else:
                alias = self._treatments.update_alias(
                    session,
                    existing_alias.id,
                    source=normalized_source,
                    external_section_name=normalized_name,
                    section_id=section_id,
                )
            self._resolve_events_for_normalized_alias(
                session,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            return alias

    def update_alias(self, alias_id: int, *, source: str, external_section_name: str, section_id: int):
        normalized_source = source.strip() or "legal_export"
        normalized_name = _normalize_external_section_name(external_section_name)
        if not normalized_name:
            raise ValueError("external_section_name must not be empty")
        with self._core.session_scope() as session:
            old_alias = self._treatments.get_alias_by_id(session, alias_id)
            if old_alias is None:
                raise ValueError(f"Could not find any treatment section alias with id {alias_id}")
            old_name = old_alias.external_section_name
            alias = self._treatments.update_alias(
                session,
                alias_id,
                source=normalized_source,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            self._resolve_events_for_normalized_alias(
                session,
                external_section_name=old_name,
                section_id=None,
            )
            self._resolve_events_for_normalized_alias(
                session,
                external_section_name=normalized_name,
                section_id=section_id,
            )
            return alias

    def delete_alias(self, alias_id: int) -> bool:
        with self._core.session_scope() as session:
            alias = self._treatments.get_alias_by_id(session, alias_id)
            if alias is None:
                return False
            external_section_name = alias.external_section_name
            deleted = self._treatments.delete_alias(session, alias_id)
            if deleted:
                self._resolve_events_for_normalized_alias(
                    session,
                    external_section_name=external_section_name,
                    section_id=None,
                )
            return deleted
