import pandas as pd
import httpx

# import geopandas as gpd
# from shapely.geometry import Point

from dataclasses import dataclass
import logging
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class StationMetadata:
    id: str
    x: float
    y: float
    crs: int = 4326
    elevation: Optional[float] = None

    @classmethod
    def from_api_payload(cls, station_id: str, metadata: dict, crs: int = 4326) -> "StationMetadata":
        return cls(
            id=station_id,
            x=metadata.get("longitude"),
            y=metadata.get("latitude"),
            crs=crs,
            elevation=metadata.get("elevation"),
        )


@dataclass
class Station:
    id: str
    x: float
    y: float
    crs: int
    elevation: Optional[float]
    data: pd.DataFrame

    def __post_init__(self):

        if self.id is None:
            raise ValueError("Station id cannot be None.")
        if self.x is None:
            raise ValueError("Station x-coordinate cannot be None.")
        if self.y is None:
            raise ValueError("Station y-coordinate cannot be None.")
        if self.crs is None:
            raise ValueError("Station crs cannot be None.")

        if self.crs != 4326:
            raise NotImplementedError(f"Station crs is {self.crs}. Only 4326 is implemented for now. Make sure the MeteoHandler returns coordinates in this crs.")

        if -90 > self.y or self.y > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if -180 > self.x or self.x > 180:
            raise ValueError("Longitude must be between -180 and 180")
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("Station data must be a pandas DataFrame.")
        if not self.data.empty and not isinstance(self.data.index, pd.DatetimeIndex):
            raise TypeError("Station data index must be a pandas DatetimeIndex.")

    @classmethod
    def create(
        cls,
        metadata: StationMetadata,
        data: pd.DataFrame,
        client: Optional[httpx.Client] = None,
        resolve_elevation: bool = False,
    ) -> "Station":

        if metadata.elevation is None and resolve_elevation:
            try:
                logger.debug("Resolving elevation for station %s", metadata.id)
                elevation = cls.fetch_elevation(metadata.x, metadata.y, client=client)
            except Exception as exc:
                logger.warning("Fetching elevation for station %s failed with error: %s", metadata.id, exc)
                elevation = None
        else:
            elevation = metadata.elevation

        return cls(
            id=metadata.id,
            x=metadata.x,
            y=metadata.y,
            data=data,
            crs=metadata.crs,
            elevation=elevation,
        )

    @property
    def latitude(self) -> float:
        return self.y

    @property
    def longitude(self) -> float:
        return self.x

    @staticmethod
    def fetch_elevation(
        x: float,
        y: float,
        client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
    ) -> float:
        api_template = "https://api.opentopodata.org/v1/eudem25m?locations={lat},{lon}"
        url = api_template.format(lat=y, lon=x)
        logger.debug(f"Requesting elevation from url: {url}")

        def _extract_elevation(response: httpx.Response) -> float:
            response.raise_for_status()
            logger.debug("Parsing elevation response payload from %s", url)
            payload = response.json()
            results = payload.get("results")
            if not isinstance(results, list) or len(results) == 0:
                raise ValueError("Elevation API returned no results.")

            elevation = results[0].get("elevation")
            if elevation is None:
                raise ValueError("Elevation API returned no elevation value.")
            logger.debug("Elevation payload parsed successfully from %s", url)
            return elevation

        if client is None:
            with httpx.Client(timeout=timeout) as temp_client:
                response = temp_client.get(url)
                return _extract_elevation(response)

        response = client.get(url, timeout=timeout)
        return _extract_elevation(response)

@dataclass
class MeteoData:
    stations: list[Station]
    crs: int

    def __post_init__(self):
        self.stations = [i for i in self.stations if i is not None]

        if len(self.stations) != len(set([i.id for i in self.stations])):
            raise ValueError("Found multiple stations with the same id in MeteoData.")

        if len(set([i.crs for i in self.stations])) > 1:
            raise ValueError("Found stations with different coordinates systems in MeteoData. Currently not supported.")

    def __repr__(self):
        return "MeteoData"

    @classmethod
    def from_list(cls, lst: list[Station | None]):
        stations = [st for st in lst if st is not None]
        if len(stations) == 0:
            return cls([], crs = 4326)
        
        crs = [i.crs for i in stations]
        if len(set(crs)) > 1:
            raise ValueError("Found stations with different coordinates systems in MeteoData. Currently not supported.")
        return cls(stations, crs = crs[0])

    @property
    def n_stations(self):
        return len(self.stations)

    @property
    def available_stations(self):
        return [i.id for i in self.stations]

    # def to_geodataframe(self):
    #     return gpd.GeoDataFrame(
    #         {'id': [st.id for st in self.stations], "geometry": [Point(st.x, st.y) for st in self.stations]},
    #         crs = self.crs
    #     )

    def to_dataframe(self, include_coords: bool = False) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for st in self.stations:
            station_id = st.id
            x = st.x
            y = st.y
            elev = st.elevation
            tbl = st.data

            if tbl is None or tbl.empty:
                continue

            df = tbl.copy()
            if isinstance(df.index, pd.DatetimeIndex):
                df.index.name = "datetime"
                df = df.reset_index()
            df["station_id"] = station_id
            df["elevation"] = elev
            if include_coords:
                df["x"] = x
                df["y"] = y
            if "datetime" in df.columns:
                df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
            frames.append(df)

        if len(frames) == 0:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    def get_station_data(self, station_id: str):
        station = next((item for item in self.stations if item.id == station_id), None)
        if station is None:
            logger.warning("No data available for station %s", station_id)
        return station
