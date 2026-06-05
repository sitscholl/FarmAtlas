import datetime

import pandas as pd

from src.metrics import (
    MetricAccumulatorService,
    calculate_days_since,
    calculate_gdd_sum,
    calculate_precipitation_sum,
)


def test_calculate_days_since():
    assert calculate_days_since(datetime.date(2026, 4, 1), datetime.date(2026, 4, 8)) == 7


def test_calculate_precipitation_sum_excludes_start_by_default():
    weather = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-01", "2026-04-02", "2026-04-03"]),
            "precipitation": [10.0, 3.0, 4.5],
        }
    )

    assert calculate_precipitation_sum(weather, "2026-04-01", "2026-04-03") == 7.5


def test_calculate_gdd_sum_uses_simple_daily_mean():
    weather = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-01", "2026-04-02", "2026-04-03"]),
            "tmin": [4.0, 10.0, 12.0],
            "tmax": [14.0, 20.0, 24.0],
        }
    )

    assert calculate_gdd_sum(weather, "2026-04-01", "2026-04-03", base_temperature=10.0) == 13.0


def test_metric_accumulator_service_delegates_weather_metrics():
    weather = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-01", "2026-04-02"]),
            "precipitation": [2.0, 6.0],
            "tmin": [8.0, 12.0],
            "tmax": [18.0, 22.0],
        }
    )
    service = MetricAccumulatorService(weather)

    assert service.precipitation_since("2026-04-01", "2026-04-02") == 6.0
    assert service.gdd_since("2026-04-01", "2026-04-02", base_temperature=10.0) == 7.0
