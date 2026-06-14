from types import SimpleNamespace
from zoneinfo import ZoneInfo
import unittest

import pandas as pd

from src.database.db import Database
from src.field_weather import FieldWeatherCacheService
from src.meteo.resample import MeteoResampler
from src.meteo.station import Station


class FakeETCalculator:
    min_rows = 3
    required_columns = (
        "tair_2m",
        "tair_2m_max",
        "tair_2m_min",
        "wind_speed",
        "solar_radiation",
        "relative_humidity",
    )

    def can_calculate(self, data: pd.DataFrame) -> bool:
        return len(data.index) >= self.min_rows and all(column in data.columns for column in self.required_columns)

    def calculate(self, station: Station, **kwargs):
        return pd.DataFrame({"et0": [4.8] * len(station.data.index)}, index=station.data.index)


class FailingETCalculator:
    min_rows = 3
    required_columns = ("relative_humidity",)

    def can_calculate(self, data: pd.DataFrame) -> bool:
        return False

    def calculate(self, station: Station, **kwargs):
        raise AssertionError("ET calculator should not be called")


class MeteoResamplerCacheTests(unittest.TestCase):
    def test_ignores_updated_at_and_keeps_all_missing_et0_as_missing(self) -> None:
        index = pd.date_range("2026-06-01", periods=24, freq="h", tz="Europe/Berlin")
        frame = pd.DataFrame(
            {
                "timestamp": index,
                "source_provider": ["demo"] * len(index),
                "source_station": ["station"] * len(index),
                "value_type": ["observed"] * len(index),
                "precipitation": [0.0] * len(index),
                "et0": [None] * len(index),
                "updated_at": [pd.Timestamp("2026-06-01T12:00:00Z")] * len(index),
            }
        )

        with self.assertNoLogs("src.meteo.resample", level="WARNING"):
            daily = MeteoResampler().apply_resampling(
                frame,
                freq="1D",
                datetime_col="timestamp",
                groupby_cols=["source_provider", "source_station", "value_type"],
            )

        self.assertNotIn("updated_at", daily.columns)
        self.assertIn("et0", daily.columns)
        self.assertTrue(pd.isna(daily.loc[0, "et0"]))

    def test_distributes_calculated_daily_et0_across_hourly_cache_rows(self) -> None:
        index = pd.date_range("2026-06-01", periods=72, freq="h", tz="Europe/Berlin")
        hourly = pd.DataFrame(
            {
                "station_id": ["station"] * len(index),
                "tair_2m": [20.0] * len(index),
                "relative_humidity": [70.0] * len(index),
                "wind_speed": [1.0] * len(index),
                "solar_radiation": [0.5] * len(index),
            },
            index=index,
        )
        service = FieldWeatherCacheService(
            db=SimpleNamespace(),
            meteo_loader=SimpleNamespace(),
            meteo_validator=SimpleNamespace(),
            meteo_resampler=MeteoResampler(),
            timezone=ZoneInfo("Europe/Berlin"),
            et_calculator=FakeETCalculator(),
            min_sample_size=20,
        )
        station = Station(
            id="station",
            x=11.0,
            y=46.0,
            crs=4326,
            elevation=250.0,
            data=hourly,
        )

        result = service._add_hourly_et0(station, hourly)

        self.assertEqual(int(result["et0"].notna().sum()), 72)
        self.assertAlmostEqual(float(result["et0"].sum()), 14.4)

    def test_skips_et0_calculation_for_incomplete_daily_inputs(self) -> None:
        index = pd.date_range("2026-06-01", periods=24, freq="h", tz="Europe/Berlin")
        hourly = pd.DataFrame(
            {
                "station_id": ["station"] * len(index),
                "tair_2m": [20.0] * len(index),
                "relative_humidity": [None] * len(index),
                "wind_speed": [1.0] * len(index),
                "solar_radiation": [0.5] * len(index),
            },
            index=index,
        )
        service = FieldWeatherCacheService(
            db=SimpleNamespace(),
            meteo_loader=SimpleNamespace(),
            meteo_validator=SimpleNamespace(),
            meteo_resampler=MeteoResampler(),
            timezone=ZoneInfo("Europe/Berlin"),
            et_calculator=FailingETCalculator(),
            min_sample_size=20,
        )
        station = Station(
            id="station",
            x=11.0,
            y=46.0,
            crs=4326,
            elevation=250.0,
            data=hourly,
        )

        result = service._add_hourly_et0(station, hourly)

        self.assertTrue(result["et0"].isna().all())

    def test_prepare_hourly_weather_ignores_provider_specific_columns(self) -> None:
        index = pd.date_range("2026-06-01", periods=3, freq="h", tz="Europe/Berlin")
        raw = pd.DataFrame(
            {
                "station_id": ["station"] * len(index),
                "precipitation": [0.0, 1.0, 0.0],
                "tair_2m": [20.0, 21.0, 22.0],
                "createdAt": ["2026-06-01"] * len(index),
                "mg15": ["raw"] * len(index),
            },
            index=index,
        )
        service = FieldWeatherCacheService(
            db=SimpleNamespace(),
            meteo_loader=SimpleNamespace(),
            meteo_validator=SimpleNamespace(),
            meteo_resampler=MeteoResampler(),
            timezone=ZoneInfo("Europe/Berlin"),
        )

        with self.assertNoLogs("src.meteo.resample", level="WARNING"):
            result = service._prepare_hourly_weather(raw)

        self.assertIn("precipitation", result.columns)
        self.assertNotIn("createdAt", result.columns)
        self.assertNotIn("mg15", result.columns)

    def test_sqlite_station_hourly_upsert_is_chunked(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamps = pd.date_range("2026-06-01", periods=120, freq="h", tz="UTC")
            weather = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "source_provider": ["demo"] * len(timestamps),
                    "source_station": ["station"] * len(timestamps),
                    "precipitation": [0.0] * len(timestamps),
                    "tair_2m": [20.0] * len(timestamps),
                    "value_type": ["observed"] * len(timestamps),
                }
            )

            with db.session_scope() as session:
                upserted = db.field_weather.add_station_hourly(session, db.engine, weather)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamps.min().to_pydatetime(),
                    end=(timestamps.max() + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(upserted, len(timestamps))
            self.assertEqual(len(rows), len(timestamps))
        finally:
            db.close()

    def test_sqlite_upsert_preserves_existing_et0_when_refresh_has_null(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamp = pd.Timestamp("2026-06-01 00:00", tz="UTC")
            original = pd.DataFrame(
                {
                    "timestamp": [timestamp],
                    "source_provider": ["demo"],
                    "source_station": ["station"],
                    "precipitation": [0.0],
                    "et0": [0.2],
                    "value_type": ["observed"],
                }
            )
            refreshed = original.copy()
            refreshed["et0"] = [None]

            with db.session_scope() as session:
                db.field_weather.add_station_hourly(session, db.engine, original)
                db.field_weather.add_station_hourly(session, db.engine, refreshed)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamp.to_pydatetime(),
                    end=(timestamp + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].et0, 0.2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
