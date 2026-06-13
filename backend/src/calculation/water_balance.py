from __future__ import annotations

import pandas as pd
from typing import Protocol


class IrrigationSeries(Protocol):
    def to_dataframe(self, index: pd.DatetimeIndex, fill_value: float = 0.0) -> pd.Series:
        ...


def calculate_water_balance(
    *,
    nfk_total_mm: float,
    daily_weather: pd.DataFrame,
    p_allowable: float,
    field_irrigation: IrrigationSeries | None = None,
    initial_storage: float | None = None,
    field_id: int | None = None,
) -> pd.DataFrame:
    if daily_weather is None or daily_weather.empty:
        raise ValueError("Daily weather cannot be empty when calculating the water balance.")
    if not isinstance(daily_weather.index, pd.DatetimeIndex):
        raise TypeError("Daily weather index must be a pandas DatetimeIndex.")
    if nfk_total_mm <= 0:
        raise ValueError("nfk_total_mm must be greater than 0.")
    if p_allowable <= 0:
        raise ValueError("p_allowable must be greater than 0.")

    data = daily_weather.sort_index().copy()
    if "precipitation" not in data.columns:
        raise KeyError("Daily weather must contain a 'precipitation' column.")

    et_column = "et0_corrected" if "et0_corrected" in data.columns else "et0" if "et0" in data.columns else None
    if et_column is None or data[et_column].isna().any():
        raise KeyError("Daily weather must contain complete 'et0_corrected' or 'et0' values.")

    precipitation = pd.to_numeric(data["precipitation"], errors="coerce").fillna(0.0)
    evapotranspiration = pd.to_numeric(data[et_column], errors="coerce").fillna(0.0)
    irrigation = (
        pd.Series(0.0, index=data.index, dtype=float)
        if field_irrigation is None
        else field_irrigation.to_dataframe(data.index, fill_value=0.0)
    )

    incoming = precipitation + irrigation
    net = incoming - evapotranspiration
    available_water_storage = float(nfk_total_mm)

    soil_water_content: list[float] = []
    current_water_content = (
        available_water_storage
        if initial_storage is None
        else max(0.0, min(available_water_storage, initial_storage))
    )
    for delta in net:
        current_water_content = max(0.0, min(available_water_storage, current_water_content + delta))
        soil_water_content.append(current_water_content)

    water_balance = pd.DataFrame(
        {
            "precipitation": precipitation,
            "irrigation": irrigation,
            "evapotranspiration": evapotranspiration,
            "incoming": incoming,
            "net": net,
            "soil_water_content": soil_water_content,
        },
        index=data.index,
    )
    water_balance["available_water_storage"] = available_water_storage
    water_balance["water_deficit"] = available_water_storage - water_balance["soil_water_content"]
    if field_id is not None:
        water_balance["field_id"] = field_id
    if "kc" in data.columns:
        water_balance["kc"] = data["kc"]

    readily_available_water = float(p_allowable) * available_water_storage
    water_balance["readily_available_water"] = readily_available_water

    trigger_level = available_water_storage - readily_available_water
    water_balance["below_raw"] = water_balance["soil_water_content"] < trigger_level
    water_balance["safe_ratio"] = (
        water_balance["soil_water_content"] - trigger_level
    ) / readily_available_water

    for column in ("model", "station_id", "source_provider", "source_station"):
        if column in data.columns:
            water_balance[column] = data[column]

    if "value_type" in data.columns:
        water_balance["value_type"] = data["value_type"].fillna("observed")
    elif "model" in data.columns:
        water_balance["value_type"] = data["model"].eq("observation").map({True: "observed", False: "forecast"})
    else:
        water_balance["value_type"] = "observed"

    return water_balance
