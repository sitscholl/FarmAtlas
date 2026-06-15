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

from src.domain.field import FieldContext
from src.database import models
from src.runtime import RuntimeContext, load_config_file
logger = logging.getLogger(__name__)


def build_runtime(temp_db_path: Path) -> RuntimeContext:
    config = load_config_file(BACKEND_ROOT / "config.example.yaml")
    config["database"] = {"path": f"sqlite:///{temp_db_path.as_posix()}"}
    runtime = RuntimeContext(config=config)
    models.Base.metadata.create_all(runtime.db.engine)
    return runtime


def seed_fields(runtime: RuntimeContext, provider: str, station_id: str, year: int) -> list[FieldContext]:
    with runtime.db.session_scope() as session:
        existing_variety = runtime.db.varieties.get_by_name(session, "Example")
        if existing_variety is None:
            runtime.db.varieties.create(session, name="Example", group="test")

    field_specs = [
        {
            "group": 'A',
            "name": "Synthetic Field A",
            "variety": "Example",
            "planting_year": 1900,
            "reference_provider": provider,
            "reference_station": station_id,
            "elevation": 0.0,
            "soil_type": "sandiger lehm",
            "soil_weight": "leicht",
            "humus_pct": 2.2,
            "effective_root_depth_cm": 35,
            "area": 16000,
            "p_allowable": 0.45,
        },
        {
            "group": 'B',
            "name": "Synthetic Field B",
            "variety": "Example",
            "planting_year": 1900,
            "reference_provider": provider,
            "reference_station": station_id,
            "elevation": 0.0,
            "soil_type": "lehm",
            "soil_weight": "mittel",
            "humus_pct": 1.8,
            "effective_root_depth_cm": 45,
            "area": 23000,
            "p_allowable": 0.50,
        },
    ]

    start_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=10)).date()
    follow_up_date = start_date + timedelta(days=4)

    for spec in field_specs:
        field_values = {
            key: spec[key]
            for key in (
                "group",
                "name",
                "reference_provider",
                "reference_station",
                "elevation",
                "soil_type",
                "soil_weight",
                "humus_pct",
                "effective_root_depth_cm",
                "p_allowable",
            )
        }
        with runtime.db.session_scope() as session:
            field_model = runtime.db.fields.create(session, **field_values)
            planting = runtime.db.plantings.create(
                session,
                field_id=field_model.id,
                variety=spec["variety"],
                valid_from=pd.Timestamp(f"{spec['planting_year']}-01-01").date(),
            )
            runtime.db.sections.create(
                session,
                planting_id=planting.id,
                name=field_model.name,
                planting_year=spec["planting_year"],
                area=spec["area"],
                valid_from=pd.Timestamp(f"{spec['planting_year']}-01-01").date(),
            )
        runtime.db.irrigation_service.create(
            field_id=field_model.id,
            date=start_date,
            method="drip",
            duration=1.0,
            amount=18.0,
        )
        runtime.db.irrigation_service.create(
            field_id=field_model.id,
            date=follow_up_date,
            method="drip",
            duration=1.0,
            amount=10.0,
        )

    logger.info("Seeded %s synthetic field(s) for year %s", len(runtime.fields), year)
    return runtime.fields

def main() -> None:
    logging.basicConfig(level=logging.INFO, force=True)

    provider = os.getenv("METEO_PROVIDER", "province")
    station_id = os.getenv("METEO_STATION_ID", "09700MS")
    forecast_days = os.getenv("FORECAST_DAYS", 7)

    with tempfile.TemporaryDirectory(prefix="irrigation_manager_wb_") as temp_dir:
        temp_db_path = Path(temp_dir) / "water_balance_test.sqlite"
        runtime = build_runtime(temp_db_path)
        try:
            year = pd.Timestamp.now(tz=runtime.timezone).year

            fields = seed_fields(runtime, provider=provider, station_id=station_id, year=year)

            logger.info(
                "Running on-demand water-balance calculation for provider=%s station_id=%s year=%s",
                provider,
                station_id,
                year,
            )
            calculation_results = runtime.water_balance_service.calculate_fields(
                fields,
                year=year,
                forecast_days=int(forecast_days),
            )

            for result in calculation_results:
                print(f"\n=== {result.field_name} ===")
                if result.warnings:
                    print("Warnings:", [warning.message for warning in result.warnings])
                if result.errors:
                    print("Errors:", [error.message for error in result.errors])
                if result.result is None or result.result.empty:
                    print("No water-balance output produced.")
                    continue
                print(result.result.tail())
        finally:
            runtime.db.close()


if __name__ == "__main__":
    main()
