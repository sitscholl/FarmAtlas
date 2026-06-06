from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pandas as pd

from .exceptions import SmartFarmerError


def _looks_like_xlsx(content: bytes, filename: str | None) -> bool:
    if filename and Path(filename).suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return True
    return content.startswith(b"PK\x03\x04")


def _column_index(cell_reference: str) -> int:
    match = re.match(r"([A-Z]+)", cell_reference)
    if match is None:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall(".//{*}si"):
        parts = [node.text or "" for node in item.findall(".//{*}t")]
        shared_strings.append("".join(parts))
    return shared_strings


def _first_worksheet_name(archive: ZipFile) -> str:
    worksheet_names = sorted(
        name
        for name in archive.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
    )
    if not worksheet_names:
        raise SmartFarmerError("Smart Farmer XLSX export contains no worksheet.")
    return worksheet_names[0]


def _cell_value(cell: ET.Element, shared_strings: list[str]):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//{*}t"))

    value_node = cell.find("{*}v")
    if value_node is None or value_node.text is None:
        return None

    raw_value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError) as exc:
            raise SmartFarmerError(f"Invalid shared string reference in XLSX: {raw_value}") from exc
    if cell_type == "b":
        return raw_value == "1"
    if cell_type in {"str", "e"}:
        return raw_value

    try:
        number = float(raw_value)
    except ValueError:
        return raw_value
    return int(number) if number.is_integer() else number


def _read_xlsx_without_styles(content: bytes) -> pd.DataFrame:
    with ZipFile(BytesIO(content)) as archive:
        shared_strings = _read_shared_strings(archive)
        worksheet_name = _first_worksheet_name(archive)
        root = ET.fromstring(archive.read(worksheet_name))

    rows: list[list[object | None]] = []
    for row in root.findall(".//{*}sheetData/{*}row"):
        values: list[object | None] = []
        for cell in row.findall("{*}c"):
            cell_reference = cell.attrib.get("r", "")
            column_index = _column_index(cell_reference)
            while len(values) <= column_index:
                values.append(None)
            values[column_index] = _cell_value(cell, shared_strings)
        if any(value is not None and value != "" for value in values):
            rows.append(values)

    if not rows:
        return pd.DataFrame()

    width = max(len(row) for row in rows)
    normalized_rows = [row + [None] * (width - len(row)) for row in rows]
    headers = ["" if value is None else str(value).strip() for value in normalized_rows[0]]
    dataframe = pd.DataFrame(normalized_rows[1:], columns=headers)

    if "Datum" in dataframe.columns and pd.api.types.is_numeric_dtype(dataframe["Datum"]):
        dataframe["Datum"] = pd.to_datetime(
            dataframe["Datum"],
            unit="D",
            origin="1899-12-30",
            errors="ignore",
        )

    return dataframe


def read_treatment_export(content: bytes, *, filename: str | None = None) -> pd.DataFrame:
    """Read a Smart Farmer treatment export into a dataframe.

    The Playwright client returns bytes so the caller does not need to persist
    browser downloads just to parse the report.
    """
    if not content:
        raise SmartFarmerError("Smart Farmer treatment export is empty.")

    if _looks_like_xlsx(content, filename):
        try:
            return pd.read_excel(BytesIO(content), engine="openpyxl")
        except Exception as exc:
            try:
                return _read_xlsx_without_styles(content)
            except Exception as fallback_exc:
                raise SmartFarmerError(
                    "Could not read Smart Farmer XLSX export with openpyxl or "
                    f"style-agnostic fallback: openpyxl={exc}; fallback={fallback_exc}"
                ) from fallback_exc

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(StringIO(content.decode(encoding)))
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            raise SmartFarmerError(f"Could not read Smart Farmer CSV export: {exc}") from exc

    raise SmartFarmerError("Could not detect Smart Farmer export format.")
