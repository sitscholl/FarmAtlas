import datetime
import logging

import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .. import models
from .fields import FieldRepository

logger = logging.getLogger(__name__)


class FieldWeatherRepository:
    HOURLY_COLUMNS = [
        "source_provider",
        "source_station",
        "timestamp",
        "precipitation",
        "tair_2m",
        "relative_humidity",
        "wind_speed",
        "wind_gust",
        "air_pressure",
        "sun_duration",
        "solar_radiation",
        "et0",
        "et0_corrected",
        "value_type",
        "updated_at",
    ]

    def __init__(self, field_repository: FieldRepository | None = None) -> None:
        self._fields = field_repository

    def list_station_hourly(
        self,
        session: Session,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | None = None,
        end: datetime.datetime | datetime.date | None = None,
    ) -> list[models.StationWeatherHourly]:
        query = session.query(models.StationWeatherHourly).filter(
            models.StationWeatherHourly.source_provider == provider,
            models.StationWeatherHourly.source_station == station,
        )
        if start is not None:
            query = query.filter(models.StationWeatherHourly.timestamp >= pd.Timestamp(start).to_pydatetime())
        if end is not None:
            query = query.filter(models.StationWeatherHourly.timestamp < pd.Timestamp(end).to_pydatetime())
        return query.order_by(models.StationWeatherHourly.timestamp).all()

    def add_station_hourly(
        self,
        session: Session,
        engine: Engine,
        hourly_weather: pd.DataFrame,
        *,
        provider: str | None = None,
        station: str | None = None,
        updated_at: datetime.datetime | None = None,
    ) -> int:
        df = hourly_weather.copy()
        if df.empty:
            return 0

        if provider is not None:
            df["source_provider"] = provider
        if station is not None:
            df["source_station"] = station
        if "timestamp" not in df.columns:
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError("Station weather dataframe must have a timestamp column or DatetimeIndex.")
            df = df.rename_axis("timestamp").reset_index()

        required_cols = ["source_provider", "source_station", "timestamp", "precipitation", "value_type"]
        missing_required = [column for column in required_cols if column not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required station weather columns: {', '.join(missing_required)}")

        optional_cols = [
            "tair_2m",
            "relative_humidity",
            "wind_speed",
            "wind_gust",
            "air_pressure",
            "sun_duration",
            "solar_radiation",
            "et0",
            "et0_corrected",
        ]
        for column in optional_cols:
            if column not in df.columns:
                df[column] = None

        if updated_at is None:
            updated_at = datetime.datetime.now(datetime.UTC)
        df["updated_at"] = pd.Timestamp(updated_at).to_pydatetime()
        df["timestamp"] = pd.to_datetime(df["timestamp"]).map(lambda value: pd.Timestamp(value).to_pydatetime())
        df["precipitation"] = pd.to_numeric(df["precipitation"], errors="coerce").fillna(0.0)

        df = df[self.HOURLY_COLUMNS]
        records = df.to_dict(orient="records")
        if not records:
            return 0

        if engine.dialect.name == "sqlite":
            stmt = sqlite_insert(models.StationWeatherHourly).values(records)
            update_cols = {
                col: getattr(stmt.excluded, col)
                for col in self.HOURLY_COLUMNS
                if col not in {"source_provider", "source_station", "timestamp"}
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    models.StationWeatherHourly.source_provider,
                    models.StationWeatherHourly.source_station,
                    models.StationWeatherHourly.timestamp,
                ],
                set_=update_cols,
            )
            result = session.execute(stmt)
            return result.rowcount or 0

        for record in records:
            session.merge(models.StationWeatherHourly(**record))
        return len(records)

    def clear_station_hourly(
        self,
        session: Session,
        *,
        provider: str,
        station: str,
        start: datetime.datetime | datetime.date | None = None,
        end: datetime.datetime | datetime.date | None = None,
        value_type: str | None = None,
    ) -> int:
        query = session.query(models.StationWeatherHourly).filter(
            models.StationWeatherHourly.source_provider == provider,
            models.StationWeatherHourly.source_station == station,
        )
        if start is not None:
            query = query.filter(models.StationWeatherHourly.timestamp >= pd.Timestamp(start).to_pydatetime())
        if end is not None:
            query = query.filter(models.StationWeatherHourly.timestamp < pd.Timestamp(end).to_pydatetime())
        if value_type is not None:
            query = query.filter(models.StationWeatherHourly.value_type == value_type)
        deleted = query.delete(synchronize_session=False)
        logger.info("Cleared %s hourly weather rows for %s/%s", deleted, provider, station)
        return deleted

    def delete_station_hourly_before(
        self,
        session: Session,
        *,
        cutoff: datetime.datetime | datetime.date,
    ) -> int:
        deleted = (
            session.query(models.StationWeatherHourly)
            .filter(models.StationWeatherHourly.timestamp < pd.Timestamp(cutoff).to_pydatetime())
            .delete(synchronize_session=False)
        )
        logger.info("Deleted %s hourly weather rows older than %s", deleted, cutoff)
        return deleted
