import pandas as pd
import pandera.pandas as pa

from .station import MeteoData, Station

class MeteoValidator:

    def __init__(self, timezone: str = 'UTC', allow_additional_columns: bool = True):
        self.timezone = timezone
        self.allow_additional_columns = allow_additional_columns

    @property
    def output_schema(self) -> pa.DataFrameSchema:
        """
        Define the expected schema for the meteo data
        """
        return pa.DataFrameSchema(
            {
                "station_id": pa.Column(str, coerce=True),
                "tair_2m": pa.Column(float, nullable=True, required=False, coerce=True),
                "relative_humidity": pa.Column(float, nullable=True, required=False, coerce=True),
                "wind_speed": pa.Column(float, nullable=True, required=False, coerce=True),
                "precipitation": pa.Column(float, nullable=True, required=False, coerce=True),
                "air_pressure": pa.Column(float, nullable=True, required=False, coerce=True),
                "sun_duration": pa.Column(float, nullable=True, required=False, coerce=True),
                "solar_radiation": pa.Column(float, nullable=True, required=False, coerce=True),
            },
            index=pa.Index(pd.DatetimeTZDtype(tz=self.timezone), coerce=True),
            strict=not self.allow_additional_columns,
        )

    def validate_dataframe(self, dataframe: pd.DataFrame, expected_station_id: str | None = None) -> pd.DataFrame:
        frame = dataframe.copy()

        if expected_station_id is not None and "station_id" not in frame.columns:
            frame["station_id"] = expected_station_id

        validated = self.output_schema.validate(frame)

        if expected_station_id is not None:
            station_ids = set(validated["station_id"].dropna().unique())
            if station_ids and station_ids != {expected_station_id}:
                raise ValueError(
                    f"Validated dataframe contains station ids {station_ids}, expected only {expected_station_id}."
                )

        return validated

    def validate(self, meteo_data: MeteoData) -> MeteoData:
        """
        Validate all station data frames in a MeteoData object.
        
        Returns a new MeteoData instance with validated/coerced station data.
        """
        validated_stations: list[Station] = []
        for station in meteo_data.stations:
            validated_stations.append(
                Station(
                    id=station.id,
                    x=station.x,
                    y=station.y,
                    crs=station.crs,
                    elevation=station.elevation,
                    data=self.validate_dataframe(station.data, expected_station_id=station.id),
                )
            )

        return MeteoData.from_list(validated_stations)
