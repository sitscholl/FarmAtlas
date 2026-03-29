import datetime
import logging

import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .. import models
from .fields import FieldRepository

logger = logging.getLogger(__name__)


class WaterBalanceRepository:
    def __init__(self, field_repository: FieldRepository) -> None:
        self._fields = field_repository

    def list_for_field(
        self,
        session: Session,
        *,
        field_id: int,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[models.WaterBalance]:
        if start is not None:
            start = pd.Timestamp(start).date()
        if end is not None:
            end = pd.Timestamp(end).date()

        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot query water balance")

        query = session.query(models.WaterBalance).filter(models.WaterBalance.field_id == field.id)
        if start is not None:
            query = query.filter(models.WaterBalance.date >= start)
        if end is not None:
            query = query.filter(models.WaterBalance.date < end)
        return query.all()

    def get_latest(
        self,
        session: Session,
        *,
        field_id: int,
        end: datetime.date | None = None,
    ) -> models.WaterBalance | None:
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot query latest water balance")

        query = session.query(models.WaterBalance).filter(models.WaterBalance.field_id == field_id)
        if end is not None:
            query = query.filter(models.WaterBalance.date < end)
        return query.order_by(models.WaterBalance.date.desc()).limit(1).one_or_none()

    def get_summary(
        self,
        session: Session,
        *,
        field_ids: list[int] | None = None,
    ) -> list[dict[str, object]]:
        field_query = session.query(models.Field).order_by(models.Field.name)
        if field_ids is not None:
            field_query = field_query.filter(models.Field.id.in_(field_ids))

        summaries: list[dict[str, object]] = []
        for field in field_query.all():
            latest_balance = self.get_latest(session, field_id=field.id)
            summaries.append(
                {
                    "field_id": field.id,
                    "as_of": None if latest_balance is None else latest_balance.date,
                    "current_water_deficit": None if latest_balance is None else latest_balance.water_deficit,
                    "current_soil_water_content": None if latest_balance is None else latest_balance.soil_water_content,
                    "available_water_storage": None if latest_balance is None else latest_balance.available_water_storage,
                    "readily_available_water": None if latest_balance is None else latest_balance.readily_available_water,
                    "below_raw": None if latest_balance is None else bool(latest_balance.below_raw),
                    "safe_ratio": None if latest_balance is None else latest_balance.safe_ratio,
                }
            )
        return summaries

    def add(self, session: Session, engine: Engine, water_balance: pd.DataFrame, *, field_id: int | None = None) -> int:
        df = water_balance.copy()
        if field_id is not None:
            df["field_id"] = field_id
        else:
            field_id_values = df["field_id"].unique()
            if len(field_id_values) > 1:
                raise ValueError(f"Found multiple field_ids for add_water_balance: {field_id_values}")
            field_id = field_id_values.item()

        if field_id is None:
            raise ValueError("Field id not provided as argument to add_water_balance and not via dataframe.")
        field = self._fields.get_by_id(session, field_id)
        if field is None:
            raise ValueError(f"Cannot find any field with id {field_id}: Cannot add_water_balance.")

        required_cols = [
            "field_id",
            "precipitation",
            "irrigation",
            "evapotranspiration",
            "incoming",
            "net",
            "soil_water_content",
            "available_water_storage",
            "water_deficit",
        ]
        optional_cols = ["readily_available_water", "safe_ratio", "below_raw"]

        missing_required = [col for col in required_cols if col not in df.columns]
        if missing_required:
            logger.warning(
                "Not all required columns to save the water balance are present. Missing: %s. Skipping insertion into database.",
                ", ".join(missing_required),
            )
            return 0

        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning(
                "Water balance index must be a pandas DatetimeIndex. Got %s. Skipping insertion into database.",
                type(df.index),
            )
            return 0

        for col in optional_cols:
            if col not in df.columns:
                df[col] = None

        extra_cols = [col for col in df.columns if col not in required_cols + optional_cols]
        if extra_cols:
            logger.info("Additional columns %s will be ignored when saving the water balance.", ", ".join(extra_cols))

        df = df.rename_axis("date").reset_index()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[["date"] + required_cols + optional_cols]

        records = df.to_dict(orient="records")
        if not records:
            logger.info("Water balance dataframe is empty. Nothing to persist.")
            return 0

        if engine.dialect.name == "sqlite":
            stmt = sqlite_insert(models.WaterBalance).values(records)
            update_cols = {
                col: getattr(stmt.excluded, col)
                for col in required_cols + optional_cols
                if col not in ("field_id", "date")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[models.WaterBalance.field_id, models.WaterBalance.date],
                set_=update_cols,
            )
            result = session.execute(stmt)
            return result.rowcount or 0

        for record in records:
            session.merge(models.WaterBalance(**record))
        return len(records)

    def clear_for_field(self, session: Session, field_id: int) -> int:
        query = session.query(models.WaterBalance).filter(models.WaterBalance.field_id == field_id)
        deleted = query.delete(synchronize_session=False)
        logger.info("Cleared %s water balance rows for field %s", deleted, field_id)
        return deleted

    def clear_all(self, session: Session) -> int:
        deleted = session.query(models.WaterBalance).delete(synchronize_session=False)
        logger.info("Cleared entire water balance cache: %s rows.", deleted)
        return deleted
