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
