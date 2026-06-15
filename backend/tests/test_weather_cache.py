from types import SimpleNamespace
from zoneinfo import ZoneInfo
import unittest

import pandas as pd

from src.database.db import Database
from src.field_weather import FieldWeatherCacheService
from src.meteo.resample import MeteoResampler


class MeteoResamplerCacheTests(unittest.TestCase):
    def test_ignores_updated_at_when_resampling_cached_weather(self) -> None:
        index = pd.date_range("2026-06-01", periods=24, freq="h", tz="Europe/Berlin")
        frame = pd.DataFrame(
            {
                "timestamp": index,
                "source_provider": ["demo"] * len(index),
                "source_station": ["station"] * len(index),
                "value_type": ["observed"] * len(index),
                "precipitation": [0.0] * len(index),
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
        self.assertIn("precipitation", daily.columns)

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

    def test_station_metadata_upsert_updates_existing_row(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            with db.session_scope() as session:
                db.field_weather.upsert_station_metadata(
                    session,
                    db.engine,
                    provider="demo",
                    station="station",
                    longitude=11.0,
                    latitude=46.0,
                    crs=4326,
                    elevation=250.0,
                )
                db.field_weather.upsert_station_metadata(
                    session,
                    db.engine,
                    provider="demo",
                    station="station",
                    longitude=11.1,
                    latitude=46.1,
                    crs=4326,
                    elevation=None,
                )
                metadata = db.field_weather.get_station_metadata(session, provider="demo", station="station")

            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.longitude, 11.1)
            self.assertEqual(metadata.latitude, 46.1)
            self.assertIsNone(metadata.elevation)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
