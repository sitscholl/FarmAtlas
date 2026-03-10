import pandas as pd
import requests

from datetime import datetime
from typing import Optional, Tuple
import logging

from .station import Station, MeteoData
from .resample import MeteoResampler

logger = logging.getLogger(__name__)

class MeteoLoader:
    """Manager class to query meteo data from multiple fields/stations and transform returned data to a consistent schema"""

    def __init__(
        self, 
        api_host: str,
        query_template: str,
        radiation_fallback_provider: str = 'province',
        radiation_fallback_station: str = '09700MS',
        request_timeout = 60
        ):
        
        self.api_host = api_host
        self.query_template = query_template

        self.radiation_fallback_provider = radiation_fallback_provider
        self.radiation_fallback_station = radiation_fallback_station
        self.request_timeout = request_timeout

        self._session = requests.Session()

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        """
        Ensure timestamps are UTC-aware to match stored station data indices.
        """
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    def _build_url(
        self,
        provider: str,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> str:
        path = self.query_template.format(
            provider=provider,
            station_id=station_id,
            start_date=start,
            end_date=end,
        ).lstrip("/")
        return f"{self.api_host}/{path}"

    def _get_data(
        self,
        provider: str,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> Tuple[pd.DataFrame, Optional[dict]]:
        url = self._build_url(provider, station_id, start, end)
        try:
            response = self._session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            payload = response.json()

            raw_data = payload.get("data", [])
            if not raw_data:
                logger.warning("No data returned for station %s (%s)", station_id, provider)
                return pd.DataFrame(), None

            response_data = pd.DataFrame(raw_data)
            response_metadata = payload.get("metadata", {})

            if "datetime" not in response_data.columns:
                logger.error("Missing 'datetime' column in response from %s", url)
                return pd.DataFrame(), None
            response_data["datetime"] = pd.to_datetime(response_data["datetime"], utc=True)

        except requests.exceptions.Timeout:
            logger.error("Request to %s timed out. Try a smaller temporal window.", url)
            return pd.DataFrame(), None

        except (requests.exceptions.RequestException, ValueError) as exc:
            logger.error("Error fetching data from %s: %s", url, exc)
            return pd.DataFrame(), None

        response_data = response_data.set_index("datetime").sort_index()
        response_data["station_id"] = station_id
        response_data = self._convert_solar_radiation_units(response_data)
        return response_data, response_metadata

    def _convert_solar_radiation_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert solar radiation readings from W/m^2 to MJ/m^2 based on the sampling interval.
        """
        if "solar_radiation" not in df.columns or df["solar_radiation"].isna().all():
            return df

        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("Cannot convert solar radiation units because dataframe index is not datetime.")
            return df

        intervals = df.index.to_series().diff().dt.total_seconds()
        positive_intervals = intervals[intervals > 0]

        if positive_intervals.empty:
            logger.warning("Unable to infer sampling interval for converting solar radiation units.")
            return df

        representative_interval = positive_intervals.median()
        intervals = intervals.fillna(representative_interval).where(intervals > 0, representative_interval)

        if intervals.isna().any() or (representative_interval is None) or representative_interval <= 0:
            logger.warning("Invalid sampling interval encountered while converting solar radiation units.")
            return df

        mj_factor = intervals / 1_000_000  # W -> J then to MJ
        converted_df = df.copy()
        converted_df["solar_radiation"] = converted_df["solar_radiation"] * mj_factor
        return converted_df

    def _fill_solar_radiation(
        self,
        df: pd.DataFrame,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        if "solar_radiation" in df.columns and df["solar_radiation"].notna().any():
            return df

        if not self.radiation_fallback_station:
            return df

        fallback_df, _ = self._get_data(
            self.radiation_fallback_provider,
            self.radiation_fallback_station,
            start,
            end,
        )

        if fallback_df.empty or "solar_radiation" not in fallback_df.columns:
            logger.warning(
                "Unable to fetch fallback solar radiation data for station %s",
                self.radiation_fallback_station,
            )
            return df

        fallback_series = (
            fallback_df["solar_radiation"]
            .reindex(df.index, method='nearest', tolerance=pd.Timedelta('3min'))
            .interpolate(method="time", limit_direction="both")
            .bfill()
        )

        if fallback_series.isna().all():
            logger.warning("Fallback solar radiation series is empty for station %s", self.radiation_fallback_station)
            return df

        df = df.copy()
        df["solar_radiation"] = fallback_series
        return df

    def _query_station(
            self, 
            provider: str, 
            station_id: str, 
            start: datetime | str, 
            end: datetime | str, #non inclusive
        ) -> Optional[Station]:
        
        try:
            df, meta = self._get_data(provider, station_id, start, end)
            metadata = meta or {}

            if df.empty:
                logger.warning("No data returned for station %s in window %s - %s", station_id, start, end)
                return None
            
            df = self._fill_solar_radiation(df, start, end)
            station = Station.create(
                id = station_id,
                elevation = metadata.get("elevation"),
                y = metadata.get("latitude"),
                x = metadata.get("longitude"),
                data = df,
                crs = 4326
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Unexpected error while fetching data for station %s: %s", station_id, exc)
            return None

        return station

    def query(
        self, 
        provider: str, 
        station_ids: list[str], 
        start: datetime | str, 
        end: datetime | str, #non inclusive
    ):
        if isinstance(station_ids, str):
            station_ids = [station_ids]

        if isinstance(start, str):
            start = pd.to_datetime(start, dayfirst=True)
        if isinstance(end, str):
            end = pd.to_datetime(end, dayfirst=True)

        start = self._to_utc(pd.to_datetime(start))
        end = self._to_utc(pd.to_datetime(end))

        if start >= end:
            raise ValueError("start must be before end")

        station_data = []
        for station_id in station_ids:
            station = self._query_station(
                provider = provider, 
                station_id = station_id, 
                start = start, 
                end = end, #non inclusive
            )
            if station is not None:
                station_data.append(station)

        return MeteoData.from_list(station_data)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from .config import load_config
    from .resample import MeteoResampler

    config = load_config('config/config.yaml')

    handler = MeteoLoader(config['meteo'])
    station = handler.query('SBR', '103', datetime(2025, 10, 1), datetime(2025, 10, 2), resampler = MeteoResampler(freq='D', min_count = 20))

    station.data['solar_radiation'].plot()
    print(station.data)
