import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.database.db import Database

logger = logging.getLogger(__name__)


FIELD_SPECS = [
    {
        "name": "Parleng",
        "reference_provider": "province",
        "reference_station": "09700MS",
        "soil_type": "sandiger lehm",
        "soil_weight": "leicht",
        "humus_pct": 2.4,
        "effective_root_depth_cm": 35,
        "area": 16000,
        "p_allowable": 0.45,
        "available_water_storage": 120.0,
        "target_safe_ratio": 0.9,
    },
    {
        "name": "Gansacker",
        "reference_provider": "province",
        "reference_station": "09700MS",
        "soil_type": "lehm",
        "soil_weight": "mittel",
        "humus_pct": 2.0,
        "effective_root_depth_cm": 45,
        "area": 22000,
        "p_allowable": 0.5,
        "available_water_storage": 150.0,
        "target_safe_ratio": 0.45,
    },
    {
        "name": "Gasslwiese",
        "reference_provider": "province",
        "reference_station": "09700MS",
        "soil_type": "lehmiger schluff",
        "soil_weight": "mittel",
        "humus_pct": 1.7,
        "effective_root_depth_cm": 40,
        "area": 11000,
        "p_allowable": 0.4,
        "available_water_storage": 135.0,
        "target_safe_ratio": 0.05,
    },
    {
        "name": "Steinacker",
        "reference_provider": "province",
        "reference_station": "09700MS",
        "soil_type": "sand",
        "soil_weight": "sehr leicht",
        "humus_pct": 1.2,
        "effective_root_depth_cm": 30,
        "area": 9000,
        "p_allowable": 0.35,
        "available_water_storage": 95.0,
        "target_safe_ratio": -0.3,
    },
]


def build_water_balance_series(
    field_id: int,
    available_water_storage: float,
    p_allowable: float,
    target_safe_ratio: float,
    end_date: pd.Timestamp,
    days: int = 14,
) -> pd.DataFrame:
    index = pd.date_range(end=end_date, periods=days, freq="D")
    raw = p_allowable * available_water_storage
    trigger_level = available_water_storage - raw

    start_safe_ratio = min(1.0, max(target_safe_ratio + 0.55, 0.2))
    ratio_step = 0.0 if days <= 1 else (target_safe_ratio - start_safe_ratio) / (days - 1)
    safe_ratios = pd.Series(
        [start_safe_ratio + ratio_step * idx for idx in range(days)],
        index=index,
        dtype=float,
    )
    soil_water_content = trigger_level + safe_ratios * raw
    soil_water_content = soil_water_content.clip(lower=0.0, upper=available_water_storage)

    evapotranspiration = pd.Series(
        [3.2, 3.5, 4.1, 4.4, 4.8, 5.0, 4.6, 4.0, 3.8, 3.6, 4.2, 4.7, 4.9, 4.3],
        index=index,
        dtype=float,
    )
    storage_delta = soil_water_content.diff().fillna(0.0)
    incoming = (storage_delta + evapotranspiration).clip(lower=0.0)

    precipitation = pd.Series(
        [0.0, 0.0, 2.5, 0.0, 0.0, 8.0, 1.0, 0.0, 0.0, 5.5, 0.0, 0.0, 1.5, 0.0],
        index=index,
        dtype=float,
    )
    irrigation = (incoming - precipitation).clip(lower=0.0)
    incoming = precipitation + irrigation
    net = incoming - evapotranspiration
    water_deficit = available_water_storage - soil_water_content
    below_raw = soil_water_content < trigger_level

    return pd.DataFrame(
        {
            "precipitation": precipitation,
            "irrigation": irrigation,
            "evapotranspiration": evapotranspiration,
            "incoming": incoming,
            "net": net,
            "soil_water_content": soil_water_content,
            "available_water_storage": available_water_storage,
            "water_deficit": water_deficit,
            "readily_available_water": raw,
            "safe_ratio": safe_ratios,
            "below_raw": below_raw,
            "field_id": field_id,
        },
        index=index,
    )


def seed_mock_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()

    db = Database(f"sqlite:///{database_path.as_posix()}", initialize_schema=True)
    end_date = pd.Timestamp.now().floor("D")

    try:
        for spec in FIELD_SPECS:
            with db.session_scope() as session:
                field = db.fields.create(
                    session,
                    name=spec["name"],
                    reference_provider=spec["reference_provider"],
                    reference_station=spec["reference_station"],
                    soil_type=spec["soil_type"],
                    soil_weight=spec["soil_weight"],
                    humus_pct=spec["humus_pct"],
                    effective_root_depth_cm=spec["effective_root_depth_cm"],
                    area=spec["area"],
                    p_allowable=spec["p_allowable"],
                    variety="Example",
                    planting_year=1900,
                )
            if field is None:
                raise RuntimeError(f"Failed to create mock field {spec['name']}")

            irrigation_dates = [end_date.date() - pd.Timedelta(days=9), end_date.date() - pd.Timedelta(days=4)]
            irrigation_amounts = [14.0, 18.0] if spec["target_safe_ratio"] >= 0 else [8.0, 10.0]
            for irrigation_date, amount in zip(irrigation_dates, irrigation_amounts):
                db.irrigation_service.create(
                    field_id=field.id,
                    date=irrigation_date,
                    method="drip",
                    amount=amount,
                )

            water_balance = build_water_balance_series(
                field_id=field.id,
                available_water_storage=spec["available_water_storage"],
                p_allowable=spec["p_allowable"],
                target_safe_ratio=spec["target_safe_ratio"],
                end_date=end_date,
            )
            with db.session_scope() as session:
                db.water_balance.add(session, db.engine, water_balance, field_id=field.id)

        logger.info("Mock database generated at %s", database_path)
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a mock IrrigationManager SQLite database for dashboard testing.",
    )
    parser.add_argument(
        "--db-path",
        default=str(BACKEND_ROOT / "mock_dashboard.sqlite"),
        help="Path to the SQLite database file to create.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, force=True)
    args = parse_args()
    database_path = Path(args.db_path).resolve()
    seed_mock_database(database_path)
    print(f"Mock database written to: {database_path}")


if __name__ == "__main__":
    main()
