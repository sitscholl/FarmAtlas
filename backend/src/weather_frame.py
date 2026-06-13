import datetime
from dataclasses import dataclass

import pandas as pd


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
