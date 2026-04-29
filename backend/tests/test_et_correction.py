from types import SimpleNamespace
import unittest

import pandas as pd

from src.et.et_correction import ETCorrection


PERIODS = [
    {"name": "Kc_ini", "value": 0.657, "start": "01-03", "end": "10-04"},
    {
        "name": "Kc_dev",
        "kind": "linear",
        "start": "10-04",
        "end": "15-06",
        "start_value": 0.657,
        "end_value": 1.013,
    },
    {"name": "Kc_mid", "value": 1.013, "start": "15-06", "end": "16-09"},
    {
        "name": "Kc_late",
        "kind": "linear",
        "start": "16-09",
        "end": "31-10",
        "start_value": 1.004,
        "end_value": 0.835,
    },
    {"name": "Kc_end", "value": 0.835, "start": "31-10", "end": "01-11"},
]


class ETCorrectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corrector = ETCorrection(PERIODS, season_end="31-10")

    def test_linear_kc_slice_matches_full_season_curve(self) -> None:
        full_season = self.corrector.to_series(pd.date_range("2026-03-01", "2026-10-31", freq="D"))
        sliced_forecast = self.corrector.to_series(pd.date_range("2026-04-29", "2026-05-05", freq="D"))

        pd.testing.assert_series_equal(
            sliced_forecast,
            full_season.reindex(sliced_forecast.index),
        )
        self.assertGreater(float(sliced_forecast.iloc[0]), 0.657)

    def test_field_kc_without_phenology_slice_matches_full_season_curve(self) -> None:
        field = SimpleNamespace(
            sections=[
                SimpleNamespace(
                    id=1,
                    active=True,
                    area=1.0,
                    phenology=[],
                )
            ]
        )

        full_season = self.corrector.to_field_series(
            pd.date_range("2026-03-01", "2026-10-31", freq="D"),
            field,
        )
        sliced_forecast = self.corrector.to_field_series(
            pd.date_range("2026-04-29", "2026-05-05", freq="D"),
            field,
        )

        pd.testing.assert_series_equal(
            sliced_forecast,
            full_season.reindex(sliced_forecast.index),
        )
        self.assertGreater(float(sliced_forecast.iloc[0]), 0.657)

    def test_field_kc_without_phenology_slice_matches_full_season_curve_with_timezone(self) -> None:
        field = SimpleNamespace(
            sections=[
                SimpleNamespace(
                    id=1,
                    active=True,
                    area=1.0,
                    phenology=[],
                )
            ]
        )

        full_season = self.corrector.to_field_series(
            pd.date_range("2026-03-01", "2026-10-31", freq="D", tz="Europe/Berlin"),
            field,
        )
        sliced_forecast = self.corrector.to_field_series(
            pd.date_range("2026-04-29", "2026-05-05", freq="D", tz="Europe/Berlin"),
            field,
        )

        pd.testing.assert_series_equal(
            sliced_forecast,
            full_season.reindex(sliced_forecast.index),
        )
        self.assertGreater(float(sliced_forecast.iloc[0]), 0.657)

    def test_field_kc_uses_maximum_section_kc(self) -> None:
        early_section = SimpleNamespace(
            id=1,
            active=True,
            area=1.0,
            phenology=[
                SimpleNamespace(date=pd.Timestamp("2026-04-01").date(), stage_code="FRUIT_SET"),
            ],
        )
        late_section = SimpleNamespace(
            id=2,
            active=True,
            area=1.0,
            phenology=[
                SimpleNamespace(date=pd.Timestamp("2026-05-20").date(), stage_code="FRUIT_SET"),
            ],
        )
        index = pd.date_range("2026-06-20", "2026-06-22", freq="D")

        field_kc = self.corrector.to_field_series(
            index,
            SimpleNamespace(sections=[early_section, late_section]),
        )
        section_kc = pd.concat(
            [
                self.corrector.to_field_series(index, SimpleNamespace(sections=[early_section])),
                self.corrector.to_field_series(index, SimpleNamespace(sections=[late_section])),
            ],
            axis=1,
        ).max(axis=1).rename("kc")

        pd.testing.assert_series_equal(field_kc, section_kc)
        self.assertEqual(float(field_kc.iloc[0]), 1.013)


if __name__ == "__main__":
    unittest.main()
