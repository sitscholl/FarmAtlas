from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import pandas as pd

from ..database.db import Database
from ..integrations.smartfarmer import (
    SmartFarmerClient,
    SmartFarmerError,
    SmartFarmerSettings,
    read_treatment_export,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TreatmentFetchResult:
    workflow_name: str
    source: str
    season_year: int
    status: str
    row_count: int = 0
    unresolved_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status != "failed"


@dataclass
class FetchTreatmentDataWorkflow:
    workflow_name: ClassVar[str] = "fetch_treatment_data"
    requires_fields: ClassVar[bool] = False

    db: Database
    settings: SmartFarmerSettings
    timezone: ZoneInfo

    @property
    def name(self) -> str:
        return self.workflow_name

    def _resolve_years(
        self,
        *,
        year: int | None = None,
        years: int | str | list[int] | None = None,
    ) -> list[int]:
        if year is not None:
            return [int(year)]
        if years is None or years == "current":
            return [pd.Timestamp.now(tz=self.timezone).year]
        if years == "current_and_previous":
            current_year = pd.Timestamp.now(tz=self.timezone).year
            return [current_year - 1, current_year]
        if isinstance(years, int):
            return [int(years)]
        if isinstance(years, list):
            return [int(value) for value in years]
        raise ValueError(
            "years must be an integer, a list of integers, 'current', or 'current_and_previous'"
        )

    def run(
        self,
        *,
        year: int | None = None,
        years: int | str | list[int] | None = None,
        source: str = "smartfarmer",
        persist: bool = True,
    ) -> list[TreatmentFetchResult]:
        resolved_years = self._resolve_years(year=year, years=years)
        results: list[TreatmentFetchResult] = []

        with SmartFarmerClient(self.settings) as client:
            for season_year in resolved_years:
                try:
                    downloaded_report = client.fetch_treatment_report(season_year)
                    dataframe = read_treatment_export(
                        downloaded_report.content,
                        filename=downloaded_report.suggested_filename,
                    )
                    metadata = {
                        "filename": downloaded_report.suggested_filename,
                        "dataframe_rows": int(len(dataframe.index)),
                    }
                    if not persist:
                        results.append(
                            TreatmentFetchResult(
                                workflow_name=self.name,
                                source=source,
                                season_year=season_year,
                                status="success",
                                row_count=int(len(dataframe.index)),
                                metadata={**metadata, "persisted": False},
                            )
                        )
                        continue

                    summary = self.db.treatment_import_service.import_full_season_dataframe(
                        dataframe=dataframe,
                        season_year=season_year,
                        source=source,
                    )
                    results.append(
                        TreatmentFetchResult(
                            workflow_name=self.name,
                            source=summary.source,
                            season_year=summary.season_year,
                            status="success" if summary.unresolved_count == 0 else "warning",
                            row_count=summary.row_count,
                            unresolved_count=summary.unresolved_count,
                            metadata={**metadata, "persisted": True},
                        )
                    )
                except (SmartFarmerError, Exception) as exc:
                    logger.exception(
                        "Fetching Smart Farmer treatment data failed for %s", season_year
                    )
                    results.append(
                        TreatmentFetchResult(
                            workflow_name=self.name,
                            source=source,
                            season_year=season_year,
                            status="failed",
                            error=str(exc),
                        )
                    )

        return results
