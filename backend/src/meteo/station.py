from dataclasses import dataclass

@dataclass
class Station:
    id: str
    elevation: float
    latitude: float
    longitude: float
    data: pd.DataFrame

    def __post_init__(self):
        if -90 > self.latitude or self.latitude > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if -180 > self.longitude or self.longitude > 180:
            raise ValueError("Longitude must be between -180 and 180")

        if self.elevation is None:
            try:
                self.elevation = self.get_elevation()
            except Exception as e:
                logger.warning(f"Fetching elevation for station {self.id} failed with error: {e}")

    def get_elevation(self):
        api_template = "https://api.opentopodata.org/v1/eudem25m?locations={lat},{lon}"
        url = api_template.format(lat=self.latitude, lon=self.longitude)
        response = requests.get(url)
        response.raise_for_status()
        elevation = response.json()["results"][0]["elevation"]
        return elevation

@dataclass
class MeteoData:
    pass