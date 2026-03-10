import pandas as pd
import pandera.pandas as pa

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
                "station_id": pa.Column(str),
                "tair_2m": pa.Column(float, nullable=True, required=False),
                "relative_humidity": pa.Column(float, nullable=True, required=False),
                "wind_speed": pa.Column(float, nullable=True, required=False),
                "precipitation": pa.Column(float, nullable=True, required=False),
                "air_pressure": pa.Column(float, nullable=True, required=False),
                "sun_duration": pa.Column(float, nullable=True, required=False),
                "solar_radiation": pa.Column(float, nullable=True, required=False),
            },
            index=pa.Index(pd.DatetimeTZDtype(tz="UTC")),
            strict=False,  # Allow additional columns that might be added
        )

    def validate(self, meteo_data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate the transformed data against the output schema.
        
        Args:
            transformed_data (pd.DataFrame): Data to validate
            
        Returns:
            pd.DataFrame: Validated data
            
        Raises:
            pa.errors.SchemaError: If validation fails
        """
        return self.output_schema.validate(meteo_data)