from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd

from .exceptions import SmartFarmerError


def _looks_like_xlsx(content: bytes, filename: str | None) -> bool:
    if filename and Path(filename).suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return True
    return content.startswith(b"PK\x03\x04")


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
            raise SmartFarmerError(f"Could not read Smart Farmer XLSX export: {exc}") from exc

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(StringIO(content.decode(encoding)))
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            raise SmartFarmerError(f"Could not read Smart Farmer CSV export: {exc}") from exc

    raise SmartFarmerError("Could not detect Smart Farmer export format.")
