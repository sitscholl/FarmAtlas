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

    def test_station_hourly_preserves_missing_precipitation(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamp = pd.Timestamp("2026-06-01T00:00:00Z")
            weather = pd.DataFrame(
                {
                    "timestamp": [timestamp],
                    "source_provider": ["demo"],
                    "source_station": ["station"],
                    "precipitation": [None],
                    "tair_2m": [20.0],
                    "value_type": ["observed"],
                }
            )

            with db.session_scope() as session:
                db.field_weather.add_station_hourly(session, db.engine, weather)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamp.to_pydatetime(),
                    end=(timestamp + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0].precipitation)
        finally:
            db.close()

    def test_station_hourly_value_columns_are_optional(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamp = pd.Timestamp("2026-06-01T00:00:00Z")
            weather = pd.DataFrame(
                {
                    "timestamp": [timestamp],
                    "source_provider": ["demo"],
                    "source_station": ["station"],
                    "value_type": ["observed"],
                }
            )

            with db.session_scope() as session:
                db.field_weather.add_station_hourly(session, db.engine, weather)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamp.to_pydatetime(),
                    end=(timestamp + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0].precipitation)
            self.assertIsNone(rows[0].tair_2m)
        finally:
            db.close()

    def test_station_hourly_upsert_does_not_overwrite_known_values_with_null(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamp = pd.Timestamp("2026-06-01T00:00:00Z")
            original = pd.DataFrame(
                {
                    "timestamp": [timestamp],
                    "source_provider": ["demo"],
                    "source_station": ["station"],
                    "precipitation": [3.5],
                    "tair_2m": [20.0],
                    "value_type": ["observed"],
                }
            )
            partial = original.copy()
            partial["precipitation"] = [None]
            partial["tair_2m"] = [None]

            with db.session_scope() as session:
                db.field_weather.add_station_hourly(session, db.engine, original)
                db.field_weather.add_station_hourly(session, db.engine, partial)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamp.to_pydatetime(),
                    end=(timestamp + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(rows[0].precipitation, 3.5)
            self.assertEqual(rows[0].tair_2m, 20.0)
        finally:
            db.close()

    def test_station_hourly_upsert_fills_existing_null_values(self) -> None:
        db = Database("sqlite:///:memory:", initialize_schema=True)
        try:
            timestamp = pd.Timestamp("2026-06-01T00:00:00Z")
            missing = pd.DataFrame(
                {
                    "timestamp": [timestamp],
                    "source_provider": ["demo"],
                    "source_station": ["station"],
                    "precipitation": [None],
                    "tair_2m": [None],
                    "value_type": ["observed"],
                }
            )
            resolved = missing.copy()
            resolved["precipitation"] = [1.25]
            resolved["tair_2m"] = [18.0]

            with db.session_scope() as session:
                db.field_weather.add_station_hourly(session, db.engine, missing)
                db.field_weather.add_station_hourly(session, db.engine, resolved)
                rows = db.field_weather.list_station_hourly(
                    session,
                    provider="demo",
                    station="station",
                    start=timestamp.to_pydatetime(),
                    end=(timestamp + pd.Timedelta(hours=1)).to_pydatetime(),
                )

            self.assertEqual(rows[0].precipitation, 1.25)
            self.assertEqual(rows[0].tair_2m, 18.0)
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
