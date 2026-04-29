from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Literal, Mapping, Sequence

import numpy as np
import pandas as pd

from ..domain.phenology import KC_PHASES_BY_NAME, PHENOLOGICAL_STAGES_BY_ANCHOR, get_phenological_stage

if TYPE_CHECKING:
    from ..field import FieldContext, SectionContext


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


def _apply_kc_period(kc: pd.Series, period: Mapping[str, object]) -> None:
    mask = (kc.index >= period["start"]) & (kc.index < period["end"])
    period_index = kc.index[mask]
    if len(period_index) == 0:
        return

    if period["kind"] == "linear":
        full_period_index = pd.date_range(
            pd.Timestamp(period["start"]),
            pd.Timestamp(period["end"]) - pd.Timedelta(days=1),
            freq="D",
        )
        if len(full_period_index) == 1:
            kc.loc[mask] = float(period["start_value"])
            return

        full_period_values = pd.Series(
            np.linspace(
                float(period["start_value"]),
                float(period["end_value"]),
                len(full_period_index),
            ),
            index=full_period_index,
            dtype=float,
        )
        kc.loc[mask] = full_period_values.reindex(period_index)
        return

    kc.loc[mask] = float(period["value"])


@dataclass(frozen=True)
class KcPeriod:
    name: str
    start: datetime | date | str
    end: datetime | date | str | None = None
    kind: Literal["constant", "linear"] = "constant"
    value: float | None = None
    start_value: float | None = None
    end_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind == "constant":
            if self.value is None:
                raise ValueError(f"KcPeriod '{self.name}' requires 'value' for constant periods.")
            if self.start_value is not None or self.end_value is not None:
                raise ValueError(
                    f"KcPeriod '{self.name}' cannot define 'start_value' or 'end_value' for constant periods."
                )
            return

        if self.kind == "linear":
            if self.start_value is None or self.end_value is None:
                raise ValueError(
                    f"KcPeriod '{self.name}' requires 'start_value' and 'end_value' for linear periods."
                )
            if self.value is not None:
                raise ValueError(f"KcPeriod '{self.name}' cannot define 'value' for linear periods.")
            return

        raise ValueError(f"Unsupported KcPeriod kind '{self.kind}' for period '{self.name}'.")

    @classmethod
    def from_spec(cls, spec: Mapping[str, object]) -> "KcPeriod":
        if "kind" in spec:
            kind = str(spec["kind"])
        elif "start_value" in spec or "end_value" in spec:
            kind = "linear"
        else:
            kind = "constant"

        return cls(
            name=str(spec["name"]),
            kind=kind,
            start=spec["start"],
            end=spec.get("end"),
            value=float(spec["value"]) if spec.get("value") is not None else None,
            start_value=float(spec["start_value"]) if spec.get("start_value") is not None else None,
            end_value=float(spec["end_value"]) if spec.get("end_value") is not None else None,
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
                    "kind": period.kind,
                    "value": period.value,
                    "start_value": period.start_value,
                    "end_value": period.end_value,
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
                    "kind": period.kind,
                    "value": period.value,
                    "start_value": period.start_value,
                    "end_value": period.end_value,
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
                _apply_kc_period(kc, period)

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

    def _observed_anchor_dates_for_section(
        self,
        section: "SectionContext",
        year: int,
        tzinfo=None,
    ) -> dict[str, pd.Timestamp]:
        observed: dict[str, pd.Timestamp] = {}
        for event in section.phenology:
            event_date = pd.Timestamp(event.date)
            if event_date.year != year:
                continue
            stage = get_phenological_stage(event.stage_code)
            if stage is None or stage.kc_anchor is None:
                continue
            observed[stage.kc_anchor] = _align_timestamp_timezone(event_date, tzinfo)
        return observed

    def _resolve_periods_for_section(
        self,
        section: "SectionContext",
        year: int,
        tzinfo=None,
    ) -> list[dict[str, object]]:
        fixed_periods = self._resolve_periods_for_year(year, tzinfo=tzinfo)
        observed = self._observed_anchor_dates_for_section(section, year, tzinfo=tzinfo)

        starts: dict[str, pd.Timestamp] = {}
        shifted_anchor = False
        previous_anchor: str | None = None

        for period, fixed in zip(self._periods, fixed_periods, strict=True):
            phase = KC_PHASES_BY_NAME.get(period.name)
            anchor = None if phase is None else phase.anchor
            fixed_start = pd.Timestamp(fixed["start"])

            if anchor is None:
                start = fixed_start
                shifted_anchor = False
            elif anchor in observed:
                start = observed[anchor]
                shifted_anchor = True
            elif previous_anchor is not None and shifted_anchor:
                previous_stage = PHENOLOGICAL_STAGES_BY_ANCHOR.get(previous_anchor)
                previous_start = starts[previous_anchor]
                if previous_stage is not None and previous_stage.default_duration is not None:
                    start = previous_start + pd.Timedelta(days=previous_stage.default_duration)
                else:
                    start = fixed_start
                    shifted_anchor = False
            else:
                start = fixed_start
                shifted_anchor = False

            if previous_anchor is not None and start <= starts[previous_anchor]:
                start = starts[previous_anchor] + pd.Timedelta(days=1)

            if anchor is not None:
                starts[anchor] = start
                previous_anchor = anchor

        resolved: list[dict[str, object]] = []
        for idx, (period, fixed) in enumerate(zip(self._periods, fixed_periods, strict=True)):
            phase = KC_PHASES_BY_NAME.get(period.name)
            anchor = None if phase is None else phase.anchor
            next_phase = KC_PHASES_BY_NAME.get(self._periods[idx + 1].name) if idx + 1 < len(self._periods) else None
            next_anchor = None if next_phase is None else next_phase.anchor

            start = starts[anchor] if anchor is not None else pd.Timestamp(fixed["start"])
            end = starts[next_anchor] if next_anchor is not None else pd.Timestamp(fixed["end"])
            if end <= start:
                end = start + pd.Timedelta(days=1)

            resolved.append(
                {
                    "name": period.name,
                    "kind": period.kind,
                    "value": period.value,
                    "start_value": period.start_value,
                    "end_value": period.end_value,
                    "start": start,
                    "end": end,
                }
            )

        return resolved

    def _section_daily_series(
        self,
        section: "SectionContext",
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.Series:
        daily_index = pd.date_range(start, end, freq="D")
        if start.tzinfo is not None and daily_index.tz is None:
            daily_index = daily_index.tz_localize(start.tzinfo)
        kc = pd.Series(index=daily_index, dtype=float, name="kc")

        for year in range(start.year, end.year + 1):
            for period in self._resolve_periods_for_section(section, year, tzinfo=daily_index.tz):
                _apply_kc_period(kc, period)

        return kc

    def to_field_series(
        self,
        target_index: pd.DatetimeIndex,
        field: "FieldContext",
    ) -> pd.Series:
        if not isinstance(target_index, pd.DatetimeIndex):
            raise TypeError("target_index must be a pandas DatetimeIndex for field-specific ET correction.")
        if target_index.empty:
            return pd.Series(index=target_index, dtype=float, name="kc")

        start_ts = target_index.min().normalize()
        end_ts = target_index.max().normalize()
        sections = [section for section in field.sections if section.active] or list(field.sections)
        if not sections:
            return self.to_series(target_index)

        weights = pd.Series(
            [max(float(section.area), 0.0) for section in sections],
            index=[section.id for section in sections],
            dtype=float,
        )
        if weights.sum() <= 0:
            weights = pd.Series(1.0, index=weights.index, dtype=float)
        weights = weights / weights.sum()

        weighted = pd.Series(0.0, index=pd.date_range(start_ts, end_ts, freq="D"), dtype=float, name="kc")
        if start_ts.tzinfo is not None and weighted.index.tz is None:
            weighted.index = weighted.index.tz_localize(start_ts.tzinfo)

        for section in sections:
            section_kc = self._section_daily_series(section, start_ts, end_ts)
            weighted = weighted.add(section_kc * weights.loc[section.id], fill_value=0.0)

        return weighted.reindex(target_index).rename("kc")

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

    def apply_to_field(
        self,
        frame: pd.DataFrame,
        column: str,
        field: "FieldContext",
    ) -> pd.DataFrame:
        kc = self.to_field_series(frame.index, field)
        corrected = frame.copy()
        corrected["kc"] = kc
        corrected[f"{column}_corrected"] = corrected[column] * kc
        return corrected


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    periods = [
        {"name": "Kc_ini", "value": 0.657, "start": "01-03"},
        {
            "name": "Kc_dev",
            "kind": "linear",
            "start": "10-04",
            "end": "15-06",
            "start_value": 0.657,
            "end_value": 1.008,
        },
        {"name": "Kc_mid", "value": 1.013, "start": "15-06", "end": "16-09"},
        {
            "name": "Kc_late",
            "kind": "linear",
            "start": "16-09",
            "end": "31-10",
            "start_value": 1.004,
            "end_value": 0.833,
        },
        {"name": "Kc_end", "value": 0.835, "start": "31-10", "end": "01-11"},
    ]

    corrector = ETCorrection(periods, season_end="31-10")
    kc = corrector.to_series(pd.date_range("2025-01-01", "2025-12-31", freq="D"))
    kc.plot()
    print(kc)
