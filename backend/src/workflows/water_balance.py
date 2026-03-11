from dataclasses import dataclass
from datetime import timedelta
import logging
from zoneinfo import ZoneInfo

import pandas as pd

from ..database.db import FarmDB
from ..et.base import ET0Calculator
from ..field import FieldContext
from ..field_capacity import calculate_field_capacity
from ..irrigation import FieldIrrigation
from ..meteo.load import MeteoLoader
from ..meteo.resample import MeteoResampler
from ..meteo.station import Station
from ..meteo.validate import MeteoValidator

logger = logging.getLogger(__name__)


@dataclass
class WaterBalanceWorkflow:
    db: FarmDB
    meteo_loader: MeteoLoader
    meteo_validator: MeteoValidator
    et_calculator: ET0Calculator
    timezone: ZoneInfo
    meteo_resampler: MeteoResampler | None = None
    min_sample_size: int = 1

    def get_cached_water_balance(
        self,
        field: FieldContext,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        if start is not None:
            start = pd.Timestamp(start)
            start = start.tz_localize(self.timezone) if start.tzinfo is None else start.tz_convert(self.timezone)
        if end is not None:
            end = pd.Timestamp(end)
            end = end.tz_localize(self.timezone) if end.tzinfo is None else end.tz_convert(self.timezone)

        records = self.db.query_water_balance(
            field_id=field.id,
            start=start.date() if start is not None else None,
            end=end.date() if end is not None else None,
        )
        if not records:
            return pd.DataFrame()

        dataframe = pd.DataFrame(
            [
                {
                    "date": record.date,
                    "precipitation": record.precipitation,
                    "irrigation": record.irrigation,
                    "evapotranspiration": record.evapotranspiration,
                    "incoming": record.incoming,
                    "net": record.net,
                    "soil_storage": record.soil_storage,
                    "field_capacity": record.field_capacity,
                    "deficit": record.deficit,
                    "readily_available_water": getattr(record, "readily_available_water", None),
                    "below_raw": getattr(record, "below_raw", None),
                    "field_id": record.field_id,
                }
                for record in records
            ]
        )
        dataframe["date"] = pd.to_datetime(dataframe["date"]).dt.tz_localize(self.timezone)
        return dataframe.set_index("date").sort_index()

    def calculate_water_balance(
        self,
        field: FieldContext,
        station_data: pd.DataFrame,
        field_irrigation: FieldIrrigation | None = None,
        initial_storage: float | None = None,
    ) -> pd.DataFrame:

        if station_data is None or station_data.empty:
            raise ValueError("Station data cannot be empty when calculating the water balance.")
        if not isinstance(station_data.index, pd.DatetimeIndex):
            raise TypeError("Station data index must be a pandas DatetimeIndex.")

        if field.field_capacity is None:
            field.field_capacity = calculate_field_capacity(
                soil_type=field.soil_type,
                humus_pct=field.humus_pct,
                root_depth_cm=field.root_depth_cm,
            )

        data = station_data.sort_index().copy()
        if data.index.tz is None:
            raise ValueError("Calculating water balance requries timezone-aware datetimes.")
        else:
            data.index = data.index.tz_convert(self.timezone)
            
        if "precipitation" not in data.columns:
            raise KeyError("Station data must contain a 'precipitation' column.")

        et_column = "et0_corrected" if "et0_corrected" in data.columns else "et0" if "et0" in data.columns else None
        if et_column is None:
            raise KeyError("Station data must contain either 'et0_corrected' or 'et0'.")

        precip = data["precipitation"].fillna(0.0)
        evap = data[et_column].fillna(0.0)
        irrigation = (
            pd.Series(0.0, index=data.index, dtype=float)
            if field_irrigation is None
            else field_irrigation.to_dataframe(data.index, fill_value=0.0)
        )

        incoming = precip + irrigation
        net = incoming - evap
        capacity = field.field_capacity.nfk_total_mm

        storage: list[float] = []
        current_storage = capacity if initial_storage is None else max(0.0, min(capacity, initial_storage))
        for delta in net:
            current_storage = max(0.0, min(capacity, current_storage + delta))
            storage.append(current_storage)

        water_balance = pd.DataFrame(
            {
                "precipitation": precip,
                "irrigation": irrigation,
                "evapotranspiration": evap,
                "incoming": incoming,
                "net": net,
                "soil_storage": storage,
            },
            index=data.index,
        )
        water_balance["field_capacity"] = capacity
        water_balance["deficit"] = capacity - water_balance["soil_storage"]
        water_balance["field_id"] = field.id

        if field.p_allowable:
            raw = field.p_allowable * capacity
            trigger_level = capacity - raw
            water_balance["readily_available_water"] = raw
            water_balance["below_raw"] = water_balance["soil_storage"] < trigger_level

        field.water_balance = water_balance
        field.results.metrics["current_soil_storage"] = float(water_balance["soil_storage"].iloc[-1])
        field.results.metrics["current_deficit"] = float(water_balance["deficit"].iloc[-1])
        return water_balance

    def _prepare_station_data(self, station: Station) -> Station:

        if self.meteo_resampler is None:
            return station

        resampled = self.meteo_resampler.apply_resampling(
            station.data.reset_index(),
            freq="D",
            min_sample_size=self.min_sample_size,
            groupby_cols = ['station_id', 'model']
        )
        resampled = resampled.set_index("datetime").sort_index()

        return Station(
            id=station.id,
            x=station.x,
            y=station.y,
            crs=station.crs,
            elevation=station.elevation,
            data=resampled,
        )

    def run_field(
        self,
        field: FieldContext,
        provider: str,
        year: int,
        season_end_utc: pd.Timestamp,
        persist: bool = True,
    ) -> pd.DataFrame | None:
        
        field_season_start = self.db.first_irrigation_event(field.id, year)
        if field_season_start is None:
            logger.info("No irrigation events found for field %s. Skipping", field.name)
            return None

        season_start_ts = pd.Timestamp(field_season_start.date, tz=self.timezone)
        latest_balance = self.db.latest_water_balance(field.id)

        if latest_balance:
            next_ts = pd.Timestamp(latest_balance.date, tz=self.timezone) + timedelta(days=1)
            start_ts = max(season_start_ts, next_ts)
            initial_storage = latest_balance.soil_storage
        else:
            start_ts = season_start_ts
            initial_storage = None

        season_end = pd.Timestamp(season_end_utc)
        season_end = season_end.tz_localize(self.timezone) if season_end.tzinfo is None else season_end.tz_convert(self.timezone)
        period_end = min(pd.Timestamp.now(tz=self.timezone).floor("D"), season_end.floor("D"))
        cache_end = period_end - pd.Timedelta(days=1)
        if start_ts >= period_end:
            cached = self.get_cached_water_balance(field, start=season_start_ts, end=cache_end)
            field.water_balance = cached if not cached.empty else None
            return field.water_balance

        meteo_data = self.meteo_loader.query(
            provider=provider,
            station_ids=[field.reference_station],
            start=start_ts,
            end=period_end,
        )
        meteo_data = self.meteo_validator.validate(meteo_data)
        station = meteo_data.get_station_data(field.reference_station)
        if station is None:
            logger.warning("No meteo station data available for field %s", field.name)
            return None

        station = self._prepare_station_data(station)
        et_data = self.et_calculator.calculate(station, correct=True)
        station.data = station.data.join(et_data)

        field.field_capacity = calculate_field_capacity(
            soil_type=field.soil_type,
            humus_pct=field.humus_pct,
            root_depth_cm=field.root_depth_cm,
        )
        irrigation_events = self.db.query_irrigation_events(field_name=field.name, year=year) or []
        field_irrigation = FieldIrrigation.from_list(irrigation_events)
        water_balance = self.calculate_water_balance(
            field=field,
            station_data=station.data,
            field_irrigation=field_irrigation,
            initial_storage=initial_storage,
        )

        if persist:
            self.db.add_water_balance(water_balance, field_id=field.id)
            cached = self.get_cached_water_balance(field, start=season_start_ts, end=cache_end)
            field.water_balance = cached if not cached.empty else water_balance

        return field.water_balance

    def run(
        self,
        fields: list[FieldContext],
        provider: str,
        year: int,
        season_end_utc: pd.Timestamp,
        persist: bool = True,
    ) -> list[FieldContext]:
        for field in fields:
            try:
                self.run_field(
                    field=field,
                    provider=provider,
                    year=year,
                    season_end_utc=season_end_utc,
                    persist=persist,
                )
            except Exception:
                logger.exception("Water balance calculation failed for field %s", field.name)
        return fields
