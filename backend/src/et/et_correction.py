from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping, Sequence

import pandas as pd


def _resolve_date_spec(value: datetime | date | str | None, anchor_year: int) -> pd.Timestamp | None:
    if value is None:
        return None

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value)

    text = str(value).strip()
    normalized = text.replace("/", "-")
    parts = [part for part in normalized.split("-") if part]

    if len(parts) == 2:
        day = int(parts[0])
        month = int(parts[1])
        return pd.Timestamp(year=anchor_year, month=month, day=day)

    return pd.to_datetime(text, dayfirst=True)


def _align_timestamp_timezone(ts: pd.Timestamp | None, tzinfo) -> pd.Timestamp | None:
    if ts is None:
        return None
    if tzinfo is None:
        return ts.tz_localize(None) if ts.tzinfo is not None else ts
    if ts.tzinfo is None:
        return ts.tz_localize(tzinfo)
    return ts.tz_convert(tzinfo)


@dataclass(frozen=True)
class KcPeriod:
    name: str
    value: float
    start: datetime | date | str
    end: datetime | date | str | None = None

    @classmethod
    def from_spec(cls, spec: Mapping[str, object]) -> "KcPeriod":
        return cls(
            name=str(spec["name"]),
            value=float(spec["value"]),
            start=spec["start"],
            end=spec.get("end"),
        )


class ETCorrection:
    """Build crop-coefficient correction curves from recurring annual Kc periods."""

    def __init__(
        self,
        periods: Sequence[KcPeriod | Mapping[str, object]],
        season_end: datetime | date | str | None = None,
    ) -> None:
        if not periods:
            raise ValueError("At least one KcPeriod is required.")

        normalized = [p if isinstance(p, KcPeriod) else KcPeriod.from_spec(p) for p in periods]
        normalized.sort(key=lambda p: _resolve_date_spec(p.start, 2000))

        self._periods = normalized
        self._season_end = season_end

    @property
    def dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "name": period.name,
                    "value": period.value,
                    "start": period.start,
                    "end": period.end,
                }
                for period in self._periods
            ]
        )

    def _resolve_periods_for_year(self, year: int, tzinfo=None) -> list[dict[str, object]]:
        season_end = _align_timestamp_timezone(_resolve_date_spec(self._season_end, year), tzinfo)
        resolved: list[dict[str, object]] = []

        for idx, period in enumerate(self._periods):
            start = _align_timestamp_timezone(_resolve_date_spec(period.start, year), tzinfo)
            next_start = (
                _align_timestamp_timezone(_resolve_date_spec(self._periods[idx + 1].start, year), tzinfo)
                if idx + 1 < len(self._periods)
                else None
            )
            end = (
                _align_timestamp_timezone(_resolve_date_spec(period.end, year), tzinfo)
                if period.end is not None
                else next_start or season_end
            )

            if end is None:
                end = pd.Timestamp(year=year + 1, month=1, day=1)
            elif end <= start:
                end = end + pd.DateOffset(years=1)

            end = _align_timestamp_timezone(pd.Timestamp(end), tzinfo)

            resolved.append(
                {
                    "name": period.name,
                    "value": period.value,
                    "start": start,
                    "end": pd.Timestamp(end),
                }
            )

        return resolved

    def as_daily_series(
        self,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> pd.Series:
        start_ts = pd.Timestamp(start) if start is not None else _resolve_date_spec(self._periods[0].start, 2000)
        end_ts = pd.Timestamp(end) if end is not None else _resolve_date_spec(self._season_end, start_ts.year)

        if start_ts is None or end_ts is None:
            raise ValueError("start and end could not be resolved for ET correction.")

        start_ts = start_ts.normalize()
        end_ts = end_ts.normalize()

        if end_ts < start_ts:
            raise ValueError("end must be on or after start for ET correction.")

        daily_index = pd.date_range(start_ts, end_ts, freq="D")
        if start_ts.tzinfo is not None and daily_index.tz is None:
            daily_index = daily_index.tz_localize(start_ts.tzinfo)
        kc = pd.Series(index=daily_index, dtype=float, name="kc")

        for year in range(start_ts.year, end_ts.year + 1):
            for period in self._resolve_periods_for_year(year, tzinfo=daily_index.tz):
                mask = (kc.index >= period["start"]) & (kc.index < period["end"])
                kc.loc[mask] = float(period["value"])

        return kc

    def as_dayofyear_series(
        self,
        start: int,
        end: int,
        anchor_year: int,
    ) -> pd.Series:
        start_date = date(anchor_year, 1, 1) + timedelta(days=start - 1)
        end_date = date(anchor_year, 1, 1) + timedelta(days=end - 1)

        daily = self.as_daily_series(start_date, end_date)
        daily.index = daily.index.dayofyear
        return daily

    def to_series(
        self,
        target_index: pd.Index,
        anchor_year: int | None = None,
    ) -> pd.Series:
        if isinstance(target_index, pd.DatetimeIndex):
            daily = self.as_daily_series(
                target_index.min().normalize(),
                target_index.max().normalize(),
            )
            return daily.reindex(target_index).rename("kc")

        if isinstance(target_index, pd.RangeIndex):
            if anchor_year is None:
                raise ValueError("anchor_year is required for RangeIndex ET correction.")
            doy_series = self.as_dayofyear_series(target_index.min(), target_index.max(), anchor_year)
            return doy_series.reindex(target_index).rename("kc")

        raise TypeError("target_index must be a pandas DatetimeIndex or RangeIndex.")

    def apply_to(
        self,
        frame: pd.DataFrame,
        column: str,
    ) -> pd.DataFrame:
        kc = self.to_series(frame.index)
        corrected = frame.copy()
        corrected["kc"] = kc
        corrected[f"{column}_corrected"] = corrected[column] * kc
        return corrected


if __name__ == "__main__":
    periods = [
        {"name": "Kc_ini", "value": 0.30, "start": "01-04"},
        {"name": "Kc_mid", "value": 1.10, "start": "01-06"},
        {"name": "Kc_end", "value": 0.65, "start": "01-07"},
    ]

    corrector = ETCorrection(periods, season_end="01-10")
    kc = corrector.to_series(pd.date_range("2025-01-01", "2025-12-31", freq="D"))
    print(kc)
