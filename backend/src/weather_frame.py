import datetime
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class WeatherColumnCompleteness:
    column: str
    missing_count: int
    present_count: int
    total_count: int

    @property
    def coverage(self) -> float | None:
        if self.total_count <= 0:
            return None
        return self.present_count / self.total_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "missing_count": self.missing_count,
            "present_count": self.present_count,
            "total_count": self.total_count,
            "coverage": self.coverage,
        }


@dataclass(frozen=True)
class WeatherCompleteness:
    resolution: str
    start: str | None
    end: str | None
    expected_count: int
    row_count: int
    missing_timestamp_count: int
    columns: dict[str, WeatherColumnCompleteness] = field(default_factory=dict)

    @property
    def missing_value_count(self) -> int:
        return sum(column.missing_count for column in self.columns.values())

    @property
    def status(self) -> str:
        if self.expected_count <= 0:
            return "missing"
        if self.row_count <= 0:
            return "missing"
        if self.missing_timestamp_count > 0 or self.missing_value_count > 0:
            return "warning"
        return "ok"

    @property
    def has_missing(self) -> bool:
        return self.status != "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution": self.resolution,
            "start": self.start,
            "end": self.end,
            "expected_count": self.expected_count,
            "row_count": self.row_count,
            "missing_timestamp_count": self.missing_timestamp_count,
            "missing_value_count": self.missing_value_count,
            "status": self.status,
            "columns": {
                column: completeness.to_dict()
                for column, completeness in self.columns.items()
            },
        }


@dataclass(frozen=True)
class WeatherFrame:
    data: pd.DataFrame
    resolution: str
    start: pd.Timestamp | None = None
    end: pd.Timestamp | None = None
    source_provider: str | None = None
    source_station: str | None = None
    refreshed: bool = False
    max_age: datetime.timedelta | None = None

    @property
    def empty(self) -> bool:
        return self.data.empty

    @property
    def updated_at(self) -> datetime.datetime | None:
        if self.data.empty or "updated_at" not in self.data.columns:
            return None

        newest_update = pd.to_datetime(self.data["updated_at"], utc=True, errors="coerce").max()
        if pd.isna(newest_update):
            return None
        return newest_update.to_pydatetime()

    def completeness(self, columns: list[str] | tuple[str, ...]) -> WeatherCompleteness:
        timestamps = self._timestamps()
        expected_index = self._expected_index(timestamps)
        if expected_index is None:
            total_count = int(len(timestamps.index))
            row_count = total_count
            missing_timestamp_count = 0
            aligned = self.data.copy()
        else:
            total_count = int(len(expected_index))
            indexed = self.data.copy()
            indexed.index = timestamps
            indexed = indexed.sort_index()
            indexed = indexed.loc[~indexed.index.duplicated(keep="last")]
            aligned = indexed.reindex(expected_index)
            row_count = int(aligned.dropna(how="all").shape[0])
            missing_timestamp_count = max(total_count - row_count, 0)

        column_results: dict[str, WeatherColumnCompleteness] = {}
        for column in columns:
            if column in aligned.columns:
                values = pd.to_numeric(aligned[column], errors="coerce")
                present_count = int(values.notna().sum())
            else:
                present_count = 0
            missing_count = max(total_count - present_count, 0)
            column_results[column] = WeatherColumnCompleteness(
                column=column,
                missing_count=missing_count,
                present_count=present_count,
                total_count=total_count,
            )

        return WeatherCompleteness(
            resolution=self.resolution,
            start=None if self.start is None else self.start.isoformat(),
            end=None if self.end is None else self.end.isoformat(),
            expected_count=total_count,
            row_count=row_count,
            missing_timestamp_count=missing_timestamp_count,
            columns=column_results,
        )

    def _timestamps(self) -> pd.DatetimeIndex:
        if "timestamp" in self.data.columns:
            return pd.DatetimeIndex(pd.to_datetime(self.data["timestamp"], errors="coerce")).dropna()
        if "datetime" in self.data.columns:
            return pd.DatetimeIndex(pd.to_datetime(self.data["datetime"], errors="coerce")).dropna()
        if isinstance(self.data.index, pd.DatetimeIndex):
            return pd.DatetimeIndex(pd.to_datetime(self.data.index, errors="coerce")).dropna()
        return pd.DatetimeIndex([])

    def _expected_index(self, timestamps: pd.DatetimeIndex) -> pd.DatetimeIndex | None:
        if self.start is None or self.end is None:
            return None

        try:
            frequency = pd.Timedelta(self.resolution)
        except ValueError:
            return None
        if frequency <= pd.Timedelta(0):
            return None

        start = pd.Timestamp(self.start)
        end = pd.Timestamp(self.end)
        if start >= end:
            return pd.DatetimeIndex([])

        if timestamps.tz is not None:
            start = start.tz_localize(timestamps.tz) if start.tz is None else start.tz_convert(timestamps.tz)
            end = end.tz_localize(timestamps.tz) if end.tz is None else end.tz_convert(timestamps.tz)
        elif start.tz is not None:
            start = start.tz_localize(None)
            end = end.tz_localize(None) if end.tz is not None else end

        return pd.date_range(start=start, end=end - frequency, freq=frequency)
