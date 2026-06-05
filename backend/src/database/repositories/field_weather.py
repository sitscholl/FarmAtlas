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
    def __init__(self, field_repository: FieldRepository) -> None:
        self._fields = field_repository

    def list_for_field(
        self,
        session: Session,
        *,
        field_id: int,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[models.FieldWeatherDaily]:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot query field weather")

        query = session.query(models.FieldWeatherDaily).filter(models.FieldWeatherDaily.field_id == field_id)
        if start is not None:
            query = query.filter(models.FieldWeatherDaily.date >= pd.Timestamp(start).date())
        if end is not None:
            query = query.filter(models.FieldWeatherDaily.date < pd.Timestamp(end).date())
        return query.order_by(models.FieldWeatherDaily.date).all()

    def add(self, session: Session, engine: Engine, daily_weather: pd.DataFrame, *, field_id: int | None = None) -> int:
        df = daily_weather.copy()
        if field_id is not None:
            df["field_id"] = field_id
        if "field_id" not in df.columns:
            raise ValueError("Field id not provided as argument and not present in dataframe.")

        required_cols = [
            "field_id",
            "precipitation",
            "source_provider",
            "source_station",
            "value_type",
        ]
        optional_cols = ["tmin", "tmax", "tmean"]
        missing_required = [column for column in required_cols if column not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required field weather columns: {', '.join(missing_required)}")

        if "date" not in df.columns:
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError("Field weather dataframe must have a date column or DatetimeIndex.")
            df = df.rename_axis("date").reset_index()

        for col in optional_cols:
            if col not in df.columns:
                df[col] = None

        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[["date"] + required_cols + optional_cols]
        records = df.to_dict(orient="records")
        if not records:
            return 0

        if engine.dialect.name == "sqlite":
            stmt = sqlite_insert(models.FieldWeatherDaily).values(records)
            update_cols = {
                col: getattr(stmt.excluded, col)
                for col in required_cols + optional_cols
                if col != "field_id"
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.FieldWeatherDaily.field_id, models.FieldWeatherDaily.date],
                set_=update_cols,
            )
            result = session.execute(stmt)
            return result.rowcount or 0

        for record in records:
            session.merge(models.FieldWeatherDaily(**record))
        return len(records)

    def clear_for_field(
        self,
        session: Session,
        *,
        field_id: int,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> int:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot clear field weather")

        query = session.query(models.FieldWeatherDaily).filter(models.FieldWeatherDaily.field_id == field_id)
        if start is not None:
            query = query.filter(models.FieldWeatherDaily.date >= pd.Timestamp(start).date())
        if end is not None:
            query = query.filter(models.FieldWeatherDaily.date < pd.Timestamp(end).date())
        deleted = query.delete(synchronize_session=False)
        logger.info("Cleared %s field weather rows for field %s", deleted, field_id)
        return deleted
