import logging
import os
import sys
import tempfile
from pathlib import Path
from datetime import timedelta

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.field import FieldContext
from src.runtime import RuntimeContext, load_config_file
logger = logging.getLogger(__name__)


def build_runtime(temp_db_path: Path) -> RuntimeContext:
    config = load_config_file(BACKEND_ROOT / "config.example.yaml")
    config["database"] = {"path": f"sqlite:///{temp_db_path.as_posix()}"}
    return RuntimeContext(config=config)


def seed_fields(runtime: RuntimeContext, provider: str, station_id: str, year: int) -> list[FieldContext]:
    field_specs = [
        {
            "name": "Synthetic Field A",
            "variety": "Example",
            "planting_year": 1900,
            "reference_provider": provider,
            "reference_station": station_id,
            "soil_type": "sandiger lehm",
            "soil_weight": "leicht",
            "humus_pct": 2.2,
            "effective_root_depth_cm": 35,
            "area_ha": 1.6,
            "p_allowable": 0.45,
        },
        {
            "name": "Synthetic Field B",
            "variety": "Example",
            "planting_year": 1900,
            "reference_provider": provider,
            "reference_station": station_id,
            "soil_type": "lehm",
            "soil_weight": "mittel",
            "humus_pct": 1.8,
            "effective_root_depth_cm": 45,
            "area_ha": 2.3,
            "p_allowable": 0.50,
        },
    ]

    start_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=10)).date()
    follow_up_date = start_date + timedelta(days=4)

    for spec in field_specs:
        field_model = runtime.db.create_field(**spec)
        runtime.db.create_irrigation_event(
            field_id=field_model.id,
            date=start_date,
            method="drip",
            amount=18.0,
        )
        runtime.db.create_irrigation_event(
            field_id=field_model.id,
            date=follow_up_date,
            method="drip",
            amount=10.0,
        )

    logger.info("Seeded %s synthetic field(s) for year %s", len(runtime.fields), year)
    return runtime.fields

def main() -> None:
    logging.basicConfig(level=logging.INFO, force=True)

    provider = os.getenv("METEO_PROVIDER", "province")
    station_id = os.getenv("METEO_STATION_ID", "09700MS")

    with tempfile.TemporaryDirectory(prefix="irrigation_manager_wb_") as temp_dir:
        temp_db_path = Path(temp_dir) / "water_balance_test.sqlite"
        runtime = build_runtime(temp_db_path)
        try:
            year = pd.Timestamp.now(tz=runtime.timezone).year

            fields = seed_fields(runtime, provider=provider, station_id=station_id, year=year)

            logger.info(
                "Running water-balance workflow for provider=%s station_id=%s year=%s",
                provider,
                station_id,
                year,
            )
            populated_fields = runtime.run_workflow_for_fields(
                workflow_name="water_balance",
                field_ids=[field.id for field in fields],
                year=year,
                persist=True,
            )

            for field in populated_fields:
                print(f"\n=== {field.name} ===")
                print("Soil water estimate:", field.soil_water_estimate)
                print("Metrics:", field.metrics)
                if field.water_balance is None or field.water_balance.empty:
                    print("No water-balance output produced.")
                    continue
                print(field.water_balance.tail())
        finally:
            runtime.db.close()


if __name__ == "__main__":
    main()
