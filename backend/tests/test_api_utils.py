import unittest

import pandas as pd

from src.api.utils import serialize_forecast_water_balance


class ApiUtilsTests(unittest.TestCase):
    def test_serialize_water_balance_accepts_named_datetime_index(self) -> None:
        index = pd.date_range("2026-06-01", periods=1, freq="D", name="datetime")
        frame = pd.DataFrame(
            {
                "precipitation": [1.0],
                "irrigation": [0.0],
                "evapotranspiration": [2.0],
                "incoming": [1.0],
                "net": [-1.0],
                "soil_water_content": [99.0],
                "available_water_storage": [100.0],
                "water_deficit": [1.0],
                "readily_available_water": [40.0],
                "safe_ratio": [1.475],
                "below_raw": [False],
                "value_type": ["observed"],
            },
            index=index,
        )

        result = serialize_forecast_water_balance(frame)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].date.isoformat(), "2026-06-01")
        self.assertEqual(result[0].evapotranspiration, 2.0)


if __name__ == "__main__":
    unittest.main()
