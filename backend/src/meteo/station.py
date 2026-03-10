import pandas as pd
import geopandas as gpd
import httpx
from shapely.geometry import Point

from dataclasses import dataclass
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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

    @classmethod
    async def create(cls, id, x, y, data, crs, elevation: Optional[float] = None, client: Optional[httpx.AsyncClient] = None):
        if elevation is None:
            try:
                elevation = await cls.fetch_elevation(x, y, client=client)
            except Exception as e:
                logger.warning(f"Fetching elevation for station {id} failed with error: {e}")
        return cls(id = id, x = x, y = y, crs = crs, elevation = elevation, data = data)

    @staticmethod
    async def fetch_elevation(x: float, y: float, client: Optional[httpx.AsyncClient] = None) -> float:
        api_template = "https://api.opentopodata.org/v1/eudem25m?locations={lat},{lon}"
        url = api_template.format(lat=y, lon=x)

        if client is None:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.get(url)
                response.raise_for_status()
                return response.json()["results"][0]["elevation"]

        response = await client.get(url)
        response.raise_for_status()
        return response.json()["results"][0]["elevation"]

@dataclass
class MeteoData:
    stations: list[Station]
    crs: str

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

    def to_geodataframe(self):
        return gpd.GeoDataFrame(
            {'id': [st.id for st in self.stations], "geometry": [Point(st.x, st.y) for st in self.stations]},
            crs = self.crs
        )

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
            df["station_id"] = station_id
            df["elevation"] = elev
            if include_coords:
                df["x"] = x
                df["y"] = y
            if "datetime" in df.columns:
                df["datetime"] = pd.to_datetime(df["datetime"])
            frames.append(df)

        if len(frames) == 0:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    def get_station_data(self, station_id: str):
        if station_id not in self.available_stations:
            logger.warning(f"No data available for station {station_id}")
            return None
        return [i for i in self.stations if i.id == station_id]