import pandas as pd

from src.application.water_balance import WaterBalanceService
from src.results import FarmAtlasWarning
from src.weather_quality import aggregate_missing_weather_warnings


class _WeatherCacheStub:
    def _to_timestamp(self, value):
        return pd.Timestamp(value)


def test_aggregate_missing_weather_warnings_collapses_matching_codes():
    warnings = [
        FarmAtlasWarning(
            message="6 daily ET input rows are missing.",
            code="WATER_BALANCE_ET_INPUTS_INCOMPLETE",
            details={"columns": ["tair_2m"], "missing_count": 6},
        ),
        FarmAtlasWarning(
            message="1 daily ET0 row is missing.",
            code="WATER_BALANCE_ET0_INCOMPLETE",
            details={"columns": ["et0"], "missing_count": 1},
        ),
        FarmAtlasWarning(
            message="3 daily corrected ET rows are missing.",
            code="WATER_BALANCE_ET_CORRECTED_INCOMPLETE",
            details={"columns": ["et0_corrected"], "missing_count": 3},
        ),
        FarmAtlasWarning(
            message="37 hourly precipitation rows are missing.",
            code="WATER_BALANCE_PRECIPITATION_INCOMPLETE",
            details={"columns": ["precipitation"], "missing_count": 37},
        ),
    ]

    result = aggregate_missing_weather_warnings(
        warnings,
        source_codes={
            "WATER_BALANCE_ET_INPUTS_INCOMPLETE",
            "WATER_BALANCE_ET0_INCOMPLETE",
            "WATER_BALANCE_ET_CORRECTED_INCOMPLETE",
        },
        code="WATER_BALANCE_EVAPOTRANSPIRATION_INCOMPLETE",
        calculation="water_balance",
        subject="evapotranspiration",
        assumption="missing_evapotranspiration_treated_as_zero",
        impact="Affected evapotranspiration rows are treated as 0.0 mm.",
    )

    assert [warning.code for warning in result] == [
        "WATER_BALANCE_EVAPOTRANSPIRATION_INCOMPLETE",
        "WATER_BALANCE_PRECIPITATION_INCOMPLETE",
    ]
    assert result[0].details["missing_count"] == 10
    assert result[0].details["source_warning_count"] == 3
    assert result[0].details["columns"] == ["et0", "et0_corrected", "tair_2m"]


def test_aggregate_missing_weather_warnings_leaves_single_warning_unchanged():
    warning = FarmAtlasWarning(
        message="1 daily ET0 row is missing.",
        code="WATER_BALANCE_ET0_INCOMPLETE",
        details={"columns": ["et0"], "missing_count": 1},
    )

    result = aggregate_missing_weather_warnings(
        [warning],
        source_codes={"WATER_BALANCE_ET0_INCOMPLETE"},
        code="WATER_BALANCE_EVAPOTRANSPIRATION_INCOMPLETE",
        calculation="water_balance",
        subject="evapotranspiration",
        assumption="missing_evapotranspiration_treated_as_zero",
        impact="Affected evapotranspiration rows are treated as 0.0 mm.",
    )

    assert result == [warning]


def test_water_balance_period_end_excludes_current_observed_day():
    service = WaterBalanceService.__new__(WaterBalanceService)
    service.timezone = "Europe/Berlin"
    service.weather_cache = _WeatherCacheStub()

    observe_end, period_end = WaterBalanceService._period_end(
        service,
        forecast_days=0,
        as_of=pd.Timestamp("2026-06-22T14:30:00+02:00"),
    )

    assert observe_end == pd.Timestamp("2026-06-22T00:00:00+02:00")
    assert period_end == pd.Timestamp("2026-06-22T00:00:00+02:00")
