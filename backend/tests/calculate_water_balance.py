import logging
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.field import FieldContext
from src.runtime import RuntimeContext, load_config_file
from src.workflows.water_balance import WaterBalanceWorkflow


logger = logging.getLogger(__name__)


def build_runtime(temp_db_path: Path) -> RuntimeContext:
    config = load_config_file(BACKEND_ROOT / "config.example.yaml")
    config["database"] = {"path": f"sqlite:///{temp_db_path.as_posix()}"}
    return RuntimeContext(config=config)


def seed_fields(runtime: RuntimeContext, station_id: str, year: int) -> list[FieldContext]:
    field_specs = [
        {
            "name": "Synthetic Field A",
            "reference_station": station_id,
            "soil_type": "sandiger lehm",
            "humus_pct": 2.2,
            "root_depth_cm": 35,
            "area_ha": 1.6,
            "p_allowable": 0.45,
        },
        {
            "name": "Synthetic Field B",
            "reference_station": station_id,
            "soil_type": "lehm",
            "humus_pct": 1.8,
            "root_depth_cm": 45,
            "area_ha": 2.3,
            "p_allowable": 0.50,
        },
    ]

    start_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=10)).date()
    follow_up_date = start_date + timedelta(days=4)

    for spec in field_specs:
        runtime.db.add_field(**spec)
        runtime.db.add_irrigation_event(
            field_name=spec["name"],
            date=start_date,
            method="drip",
            amount=18.0,
        )
        runtime.db.add_irrigation_event(
            field_name=spec["name"],
            date=follow_up_date,
            method="drip",
            amount=10.0,
        )

    runtime.fields = [FieldContext.from_model(field) for field in runtime.db.get_all_fields()]
    logger.info("Seeded %s synthetic field(s) for year %s", len(runtime.fields), year)
    return runtime.fields


def build_workflow(runtime: RuntimeContext) -> WaterBalanceWorkflow:
    return WaterBalanceWorkflow(
        db=runtime.db,
        meteo_loader=runtime.meteo_loader,
        meteo_validator=runtime.meteo_validator,
        et_calculator=runtime.et_calculator,
        timezone=runtime.timezone,
        meteo_resampler=runtime.meteo_resampler,
        min_sample_size=int(runtime.min_sample_size),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, force=True)

    provider = os.getenv("METEO_PROVIDER", "province")
    station_id = os.getenv("METEO_STATION_ID", "09700MS")

    with tempfile.TemporaryDirectory(prefix="irrigation_manager_wb_") as temp_dir:
        temp_db_path = Path(temp_dir) / "water_balance_test.sqlite"
        runtime = build_runtime(temp_db_path)

        now = pd.Timestamp.now(tz=runtime.timezone)
        year = now.year
        season_end = now.floor("D") + pd.Timedelta(days=1)

        fields = seed_fields(runtime, station_id=station_id, year=year)
        workflow = build_workflow(runtime)

        logger.info(
            "Running water-balance workflow for provider=%s station_id=%s season_end=%s",
            provider,
            station_id,
            season_end,
        )
        populated_fields = workflow.run(
            fields=fields,
            provider=provider,
            year=year,
            season_end=season_end,
            persist=True,
        )

        for field in populated_fields:
            print(f"\n=== {field.name} ===")
            print("Field capacity:", field.field_capacity)
            print("Metrics:", field.results.metrics)
            if field.water_balance is None or field.water_balance.empty:
                print("No water-balance output produced.")
                continue
            print(field.water_balance.tail())


if __name__ == "__main__":
    main()
