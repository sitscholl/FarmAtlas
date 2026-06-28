import unittest

import pandas as pd

from src.calculation.water_balance import calculate_water_balance


class WaterBalanceCalculationTests(unittest.TestCase):
    def test_safe_ratio_uses_total_available_storage(self) -> None:
        daily_weather = pd.DataFrame(
            {
                "precipitation": [0.0, 0.0, 0.0, 0.0],
                "et0": [25.0, 25.0, 25.0, 25.0],
            },
            index=pd.date_range("2026-06-01", periods=4, freq="D"),
        )

        result = calculate_water_balance(
            nfk_total_mm=100.0,
            daily_weather=daily_weather,
            p_allowable=0.4,
        )

        self.assertEqual(result["soil_water_content"].tolist(), [75.0, 50.0, 25.0, 0.0])
        self.assertEqual(result["safe_ratio"].tolist(), [0.75, 0.5, 0.25, 0.0])
        self.assertEqual(result["below_raw"].tolist(), [False, True, True, True])


if __name__ == "__main__":
    unittest.main()
