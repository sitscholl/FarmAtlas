import datetime
import logging
from contextlib import contextmanager
from typing import Generator, List, Optional, Any

from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker
import pandas as pd

from . import models

logger = logging.getLogger(__name__)


class FarmDB:
    WATER_BALANCE_TRIGGER_FIELDS = {
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
        "reference_provider",
        "reference_station",
    }

    _UPDATE_FIELD_ALLOWLIST = {
        "name",
        "section",
        "variety",
        "planting_year",
        "area_ha",
        "tree_count",
        "tree_height",
        "row_distance",
        "tree_distance",
        "running_metre",
        "herbicide_free",
        "active",
        "reference_provider",
        "reference_station",
        "soil_type",
        "soil_weight",
        "humus_pct",
        "effective_root_depth_cm",
        "p_allowable",
    }
    _UPDATE_IRRIGATION_ALLOWLIST = {"field_id", "date", "method", "amount"}

    def __init__(self, engine_url: str = 'sqlite:///database.db', **engine_kwargs) -> None:
        """
        Create a database engine and initialise ORM metadata.
        """
        self.engine = create_engine(engine_url, future=True, **engine_kwargs)
        models.Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        """
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """
        Dispose of the database engine connection pool.
        """
        if self.engine:
            self.engine.dispose()
            logger.debug("Database engine disposed.")

    ## Fields
    def _get_field(self, session: Session, id: int) -> Optional[models.Field]:
        return (
            session.query(models.Field)
            .filter(models.Field.id == id)
            .one_or_none()
        )

    def get_field(self, id: int) -> models.Field | None:
        """
        Retrieve a field by its unique name or its id.
        """
        with self.session_scope() as session:
            return (
                session.query(models.Field)
                .filter(models.Field.id == id)
                .one_or_none()
            )

    def list_fields(self) -> List[models.Field]:
        """
        Return the distinct field names sorted alphabetically.
        """
        with self.session_scope() as session:
            fields = (
                session.query(models.Field)
                .order_by(models.Field.id)
                .all()
            )
        return fields

    def create_field(
        self,
        name: str,
        variety: str,
        planting_year: int,
        reference_provider: str,
        reference_station: str,
        soil_type: str,
        soil_weight: str | None,
        humus_pct: float,
        area_ha: float,
        effective_root_depth_cm: float,
        p_allowable: float,
        section: str | None = None,
        tree_count: int | None = None,
        tree_height: float | None = None,
        row_distance: float | None = None,
        tree_distance: float | None = None,
        running_metre: float | None = None,
        herbicide_free: bool | None = None,
        active: bool = True,
    ) -> models.Field:

        section = None if section in (None, "") else str(section)
        variety = str(variety)
        planting_year = int(planting_year)
        reference_provider = str(reference_provider)
        reference_station = str(reference_station)
        soil_type = str(soil_type)
        soil_weight = None if soil_weight in (None, "") else str(soil_weight)
        humus_pct = float(humus_pct)
        effective_root_depth_cm = float(effective_root_depth_cm)
        area_ha_value = float(area_ha)
        p_allowable_value = float(p_allowable)
        tree_count_value = None if tree_count is None else int(tree_count)
        tree_height_value = None if tree_height is None else float(tree_height)
        row_distance_value = None if row_distance is None else float(row_distance)
        tree_distance_value = None if tree_distance is None else float(tree_distance)
        running_metre_value = None if running_metre is None else float(running_metre)
        herbicide_free_value = None if herbicide_free is None else bool(herbicide_free)
        active_value = bool(active)

        with self.session_scope() as session:
            field = models.Field(
                name=name,
                section=section,
                variety=variety,
                planting_year=planting_year,
                tree_count=tree_count_value,
                tree_height=tree_height_value,
                row_distance=row_distance_value,
                tree_distance=tree_distance_value,
                running_metre=running_metre_value,
                herbicide_free=herbicide_free_value,
                active=active_value,
                reference_provider=reference_provider,
                reference_station=reference_station,
                soil_type=soil_type,
                soil_weight=soil_weight,
                humus_pct=humus_pct,
                effective_root_depth_cm=effective_root_depth_cm,
                area_ha=area_ha_value,
                p_allowable=p_allowable_value,
            )
            session.add(field)
            session.flush()  # ensure primary key is populated for new records
            logger.debug(f"Added new field {field} to database")
        return field

    def update_field(
        self,
        id: int,
        updates: dict[str, Any]
    ) -> models.Field:

        updated = False
        changed_keys: set[str] = set()
        with self.session_scope() as session:
            existing_field = self._get_field(session = session, id = id)
            if existing_field is None:
                raise ValueError(f"Could not find any field with id {id}")

            for field_key, new_value in updates.items():
                if field_key not in self._UPDATE_FIELD_ALLOWLIST:
                    raise ValueError(f"Invalid key {field_key} in update_field. Choose one of {self._UPDATE_FIELD_ALLOWLIST}")

                if getattr(existing_field, field_key) != new_value:
                    setattr(existing_field, field_key, new_value)
                    updated = True
                    changed_keys.add(field_key)

            if not updated:
                logger.debug(f"No changes for field {existing_field}; skipping update")
                return existing_field
            elif changed_keys & self.WATER_BALANCE_TRIGGER_FIELDS:
                logger.info(f"Updated field {existing_field}. Deleting existing water-balance cache")
                _ = self._clear_water_balance(session, field_id = existing_field.id)

            session.flush()  # ensure primary key is populated for new records
        return existing_field

    def delete_field(self, id: int) -> bool:
        with self.session_scope() as session:
            field = self._get_field(session = session, id = id)
            if not field:
                return False
            session.delete(field)
        return True

    ## Irrigation
    def list_irrigation_events(
        self, 
        field_id: int | None = None, 
        start: datetime.date = None, 
        end: datetime.date = None
        ) -> list[models.Irrigation] | None:
        if start is not None:
            start = pd.Timestamp(start).date()
        if end is not None:
            end = pd.Timestamp(end).date()

        with self.session_scope() as session:
            query = session.query(models.Irrigation)
            if field_id is not None:
                field = self._get_field(session, id = field_id)
                if field is None:
                    raise ValueError(
                       f"No field with id {field_id} found. Cannot query irrigation event",
                    )
                query = query.filter(models.Irrigation.field_id == field_id)

            if start is not None:
                query = query.filter(models.Irrigation.date >= start)
            if end is not None:
                query = query.filter(models.Irrigation.date < end)

            return query.all()

    def get_first_irrigation_event(self, field_id: int, year: int) -> Optional[models.Irrigation]:
        with self.session_scope() as session:
            return (
                session.query(models.Irrigation)
                .filter(models.Irrigation.field_id == field_id)
                .filter(models.Irrigation.date >= datetime.date(year, 1, 1), models.Irrigation.date < datetime.date(year+1, 1, 1))
                .order_by(models.Irrigation.date.asc())
                .limit(1)
                .one_or_none()
            )

    def create_irrigation_event(
        self,
        field_id: int,
        date: datetime.date,
        method: str,
        amount: float,
    ) -> models.Irrigation:
        
        if isinstance(date, str):
            date = pd.Timestamp(date).date()

        with self.session_scope() as session:
            field = self._get_field(session, id = field_id)
            if field is None:
                raise ValueError(f"No field with id '{field_id}' found")

            event = models.Irrigation(
                field_id=field.id,
                date=date,
                method=method,
                amount=amount,
            )
            session.add(event)
            session.flush()
            logger.debug(f"Created new irrigation event for field {field}")

            self._clear_water_balance(session, field_id = field.id)

        return event

    def update_irrigation_event(self, event_id: int, updates: dict[str, Any]) -> models.Irrigation:
        updated = False
        with self.session_scope() as session:
            existing_event = session.query(models.Irrigation).filter(models.Irrigation.id == event_id).one_or_none()
            if existing_event is None:
                raise ValueError(f"Could not find any irrigation event with id {event_id}")

            old_field_id = None
            for field_key, new_value in updates.items():
                if field_key not in self._UPDATE_IRRIGATION_ALLOWLIST:
                    raise ValueError(f"Invalid key {field_key} in update_irriation_event. Choose one of {self._UPDATE_IRRIGATION_ALLOWLIST}")

                if getattr(existing_event, field_key) != new_value and new_value is not None:

                    if field_key == 'field_id':
                        new_field = self._get_field(session = session, id = new_value)
                        if new_field is None:
                            raise ValueError(f"Invalid new field id {new_value} in update_irrigation_event.")
                        old_field_id = existing_event.field_id

                    if field_key == 'date':
                        new_value = pd.Timestamp(new_value).date()

                    setattr(existing_event, field_key, new_value)
                    updated = True

            if not updated:
                logger.debug(f"No changes for irrigation_event {existing_event}; skipping update")
                return existing_event
            else:
                logger.info(f"Updated irrigation event {existing_event}. Deleting existing water-balance cache")
                _ = self._clear_water_balance(session, field_id = existing_event.field_id)
                
                if old_field_id:
                    self._clear_water_balance(session, field_id=old_field_id)

            session.flush()  # ensure primary key is populated for new records
        return existing_event

    def delete_irrigation_event(self, event_id: int) -> bool:
        with self.session_scope() as session:
            event = session.get(models.Irrigation, event_id)
            if not event:
                return False
            session.delete(event)
            self._clear_water_balance(session, field_id = event.field_id)
            return True

    ## Water Balance
    def get_water_balance(
        self, 
        field_id: int,
        start: datetime.date | None = None, 
        end: datetime.date | None = None
        ) -> list[models.WaterBalance]:

        if start is not None:
            start = pd.Timestamp(start).date()
        if end is not None:
            end = pd.Timestamp(end).date()
        
        with self.session_scope() as session:
            field = self._get_field(session, id = field_id)
            if field is None:
                raise ValueError(f"No field with id {field_id} found. Cannot query water balance")
            query = session.query(models.WaterBalance).filter(models.WaterBalance.field_id == field.id)

            if start is not None:
                query = query.filter(models.WaterBalance.date >= start)
            if end is not None:
                query = query.filter(models.WaterBalance.date < end)

            return query.all()

    def _get_latest_water_balance(
        self, session: Session, field_id: int
    ) -> Optional[models.WaterBalance]:

        field = self._get_field(session, id = field_id)
        if field is None:
            raise ValueError(f"No field with id {field_id} found. Cannot query latest water balance")

        return (
            session.query(models.WaterBalance)
            .filter(models.WaterBalance.field_id == field_id)
            .order_by(models.WaterBalance.date.desc())
            .limit(1)
            .one_or_none()
        )

    def get_latest_water_balance(self, field_id: int) -> models.WaterBalance | None:
        with self.session_scope() as session:
            return self._get_latest_water_balance(session = session, field_id = field_id)

    def get_water_balance_summary(self, field_ids: list[int] | None = None) -> list[dict[str, object]]:
        with self.session_scope() as session:
            field_query = session.query(models.Field).order_by(models.Field.name)
            if field_ids is not None:
                field_query = field_query.filter(models.Field.id.in_(field_ids))

            summaries: list[dict[str, object]] = []
            for field in field_query.all():
                latest_balance = self._get_latest_water_balance(session, field.id)
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

    def add_water_balance(self, water_balance: pd.DataFrame, field_id: int | None = None) -> int:
        """
        Upsert water balance records from a dataframe.
        Returns the number of rows inserted/updated.
        """
        df = water_balance.copy()
        if field_id is not None:
            df["field_id"] = field_id
        else:
            field_id = df['field_id'].unique()
            if len(field_id) > 1:
                raise ValueError(f"Found multiple field_ids for add_water_balance: {field_id}")
            field_id = field_id.item()

        if field_id is None:
            raise ValueError("Field id not provided as argument to add_water_balance and not via dataframe.")
        field = self.get_field(id = field_id)
        if field is None:
            raise ValueError(f"Cannot find any field with id {field_id}: Cannot add_water_balance.")

        required_cols = [
            'field_id',
            'precipitation',
            'irrigation',
            'evapotranspiration',
            'incoming',
            'net',
            'soil_water_content',
            'available_water_storage',
            'water_deficit',
        ]
        optional_cols = ['readily_available_water', 'safe_ratio', 'below_raw']

        missing_required = [col for col in required_cols if col not in df.columns]
        if missing_required:
            logger.warning(
                "Not all required columns to save the water balance are present. Missing: %s. "
                "Skipping insertion into database.",
                ", ".join(missing_required),
            )
            return 0

        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning(
                "Water balance index must be a pandas DatetimeIndex. Got %s. "
                "Skipping insertion into database.",
                type(df.index),
            )
            return 0

        for col in optional_cols:
            if col not in df.columns:
                df[col] = None

        extra_cols = [col for col in df.columns if col not in required_cols + optional_cols]
        if extra_cols:
            logger.info(
                "Additional columns %s will be ignored when saving the water balance.",
                ", ".join(extra_cols),
            )

        df = df.rename_axis("date").reset_index()
        # Water-balance rows are daily aggregates keyed by calendar day, so preserve the
        # existing day semantics instead of converting through UTC and shifting dates.
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[["date"] + required_cols + optional_cols]

        records = df.to_dict(orient="records")
        if not records:
            logger.info("Water balance dataframe is empty. Nothing to persist.")
            return 0

        # Use SQLite upsert for performance; fall back to per-row merge for other dialects.
        if self.engine.dialect.name == "sqlite":
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

            with self.session_scope() as session:
                result = session.execute(stmt)
                return result.rowcount or 0

        with self.session_scope() as session:
            for record in records:
                session.merge(models.WaterBalance(**record))
            return len(records)

    def _clear_water_balance(self, session: Session, field_id: int) -> int:
        query = session.query(models.WaterBalance).filter(models.WaterBalance.field_id == field_id)
        deleted = query.delete(synchronize_session=False)
        logger.info(f"Cleared {deleted} water balance rows for field {field_id}")
        return deleted

    def clear_water_balance(self, field_ids: list[int] | int | None = None) -> int:
        """
        Delete water balance entries. If field_ids provided, only delete those.
        Returns number of rows deleted.
        """

        if field_ids is None:
            with self.session_scope() as session:
                query = session.query(models.WaterBalance)
                deleted = query.delete(synchronize_session=False)
                logger.info(f"Cleared entire water balance cache: {deleted} rows.")
                return deleted

        if isinstance(field_ids, int):
            field_ids = [field_ids]

        deleted_total = 0
        for field_id in field_ids:
            with self.session_scope() as session:
                deleted = self._clear_water_balance(session, field_id)
                deleted_total += deleted
        return deleted_total

if __name__ == '__main__':
    import logging.config
    import pandas as pd

    # from ..config import load_config

    # config = load_config('config/config.yaml')
    # logging.config.dictConfig(config['logging'])

    db = FarmDB()

    fields = db.list_fields()

    for date in pd.date_range("04-01-2025", "10-01-2025", freq = "2W"):
        for field in fields:
            db.create_irrigation_event(
                field_name=field.name,
                date=date.date(),
                method='drip',
            )

    print('Fields in database:')
    print(db.list_fields())

    db.close()
