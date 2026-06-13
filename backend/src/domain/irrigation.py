from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import pandas as pd


class IrrigationEventLike(Protocol):
    field_id: int
    date: date | datetime
    amount: float


@dataclass(slots=True)
class FieldIrrigation:
    field_id: int
    dates: list[pd.Timestamp]
    amounts: list[float]

    def __init__(
        self,
        field_id: int,
        dates: Sequence[date | datetime | pd.Timestamp],
        amounts: Sequence[float],
    ) -> None:
        if len(dates) != len(amounts):
            raise ValueError(f"Dates and amounts must have the same length. Got {len(dates)} dates and {len(amounts)} amounts.")

        normalized_dates: list[pd.Timestamp] = []
        for value in dates:
            timestamp = pd.Timestamp(value)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
            normalized_dates.append(timestamp)

        self.field_id = int(field_id)
        self.dates = normalized_dates
        self.amounts = [float(amount) for amount in amounts]

    @classmethod
    def from_list(cls, irrigation_events: Iterable[IrrigationEventLike]) -> "FieldIrrigation | None":
        events = list(irrigation_events)
        if not events:
            return None

        field_ids = {int(event.field_id) for event in events}
        if len(field_ids) > 1:
            raise ValueError("Multiple fields found. Cannot initialize FieldIrrigation from list of irrigation events.")

        field_id = field_ids.pop()
        irrigation_dates = [event.date for event in events]
        irrigation_amounts = [event.amount for event in events]

        return cls(field_id, irrigation_dates, irrigation_amounts)

    def to_dataframe(self, index: pd.DatetimeIndex, fill_value: float = 0.0) -> pd.Series:
        if not isinstance(index, pd.DatetimeIndex):
            raise ValueError("Index must be a pandas DatetimeIndex.")

        irrigation = pd.DataFrame(
            {
                "date": self.dates,
                "amount": self.amounts,
            }
        ).set_index("date")

        irrigation = irrigation.sort_index()
        target_tz = index.tz
        if target_tz is not None:
            if irrigation.index.tz is None:
                irrigation.index = irrigation.index.tz_localize(target_tz)
            else:
                irrigation.index = irrigation.index.tz_convert(target_tz)
        elif irrigation.index.tz is not None:
            irrigation.index = irrigation.index.tz_localize(None)

        daily = irrigation["amount"].fillna(0.0).groupby(irrigation.index.normalize()).sum()
        aligned = daily.reindex(index.normalize(), fill_value=fill_value)
        aligned.index = index
        return aligned.astype(float)
