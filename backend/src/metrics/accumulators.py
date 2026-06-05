import datetime
from dataclasses import dataclass

import pandas as pd

from .gdd import calculate_gdd_sum
from .periods import calculate_days_since
from .precipitation import calculate_precipitation_sum


@dataclass(frozen=True)
class MetricAccumulatorService:
    daily_weather: pd.DataFrame

    def days_since(
        self,
        start_date: datetime.date | str,
        end_date: datetime.date | str | None = None,
    ) -> int:
        return calculate_days_since(start_date, end_date)

    def precipitation_since(
        self,
        start_date: datetime.date | str,
        end_date: datetime.date | str | None = None,
        *,
        include_start: bool = False,
    ) -> float:
        return calculate_precipitation_sum(
            self.daily_weather,
            start_date,
            end_date,
            include_start=include_start,
        )

    def gdd_since(
        self,
        start_date: datetime.date | str,
        end_date: datetime.date | str | None = None,
        *,
        base_temperature: float,
        include_start: bool = False,
    ) -> float:
        return calculate_gdd_sum(
            self.daily_weather,
            start_date,
            end_date,
            base_temperature=base_temperature,
            include_start=include_start,
        )
