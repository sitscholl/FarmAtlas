import argparse
import datetime
import sys
from pathlib import Path
from textwrap import dedent

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.db import Database
from src.metrics import MetricAccumulatorService
from src.schemas import CropProtectionRuleEvaluationRead, CropProtectionRuleRead


def step(title: str, *, debug: bool) -> None:
    print(f"\n=== {title} ===")
    if debug:
        breakpoint()


def main() -> None:
    parser = argparse.ArgumentParser(description="Step through the crop-protection backend workflow.")
    parser.add_argument("--debug", action="store_true", help="Open breakpoint() at each workflow step.")
    args = parser.parse_args()

    db = Database("sqlite:///:memory:", initialize_schema=True)

    step("1. Create a tiny in-memory farm structure", debug=args.debug)
    with db.session_scope() as session:
        field = db.fields.create(
            session,
            group="Demo",
            name="Demo Field",
            reference_provider="demo",
            reference_station="demo-station",
            elevation=250,
        )
        db.varieties.create(session, name="Gala", group="apple")
        planting = db.plantings.create(
            session,
            field_id=field.id,
            variety="Gala",
            valid_from=datetime.date(2026, 1, 1),
        )
        section = db.sections.create(
            session,
            planting_id=planting.id,
            name="Demo Section",
            planting_year=2020,
            area=1000,
            valid_from=datetime.date(2026, 1, 1),
        )
        field_id = field.id
        section_id = section.id
    print(f"Created field_id={field_id}, section_id={section_id}")

    step("2. Import a legal-export CSV row before any alias exists", debug=args.debug)
    csv_text = dedent(
        """\
        Datum,Anlage,Mittel,Dosis /hl 1x,hl 1x,Grund,Kosten
        01/04/2026,External Demo Section,Delan 70 WG,25.5,3.0,Apfelschorf,12.50 €
        """
    )
    summary = db.treatment_import_service.import_full_season_csv(
        csv_text=csv_text,
        season_year=2026,
        source="debug_export",
    )
    print(f"Imported rows={summary.row_count}, unresolved={summary.unresolved_count}")

    step("3. Create a section alias and let it resolve existing treatment rows", debug=args.debug)
    alias = db.treatment_import_service.create_alias(
        source="debug_export",
        external_section_name="External Demo Section",
        section_id=section_id,
    )
    with db.session_scope() as session:
        unresolved = db.treatments.unresolved_external_section_names(
            session,
            source="debug_export",
            season_year=2026,
        )
        events = db.treatments.list_events(session, source="debug_export", season_year=2026)
    print(f"Created alias_id={alias.id}; unresolved names now={unresolved}")
    print(f"Resolved treatment section_id={events[0].section_id}, product={events[0].product_name}")

    step("4. Add daily field weather cache rows", debug=args.debug)
    weather = pd.DataFrame(
        {
            "date": pd.date_range("2026-04-01", "2026-04-10", freq="D"),
            "precipitation": [0, 2, 3, 1, 0, 4, 2, 0, 1, 2],
            "tmin": [8, 9, 10, 11, 8, 9, 12, 13, 10, 11],
            "tmax": [18, 19, 20, 21, 18, 19, 22, 23, 20, 21],
            "source_provider": "demo",
            "source_station": "demo-station",
            "value_type": "observed",
        }
    )
    weather["tmean"] = (weather["tmin"] + weather["tmax"]) / 2
    with db.session_scope() as session:
        upserted = db.field_weather.add(session, db.engine, weather, field_id=field_id)
        cached_weather = db.field_weather.list_for_field(
            session,
            field_id=field_id,
            start=datetime.date(2026, 4, 1),
            end=datetime.date(2026, 4, 11),
        )
    print(f"Upserted weather rows={upserted}; cached rows={len(cached_weather)}")

    step("5. Calculate metrics directly from the cached weather", debug=args.debug)
    weather_frame = pd.DataFrame(
        [
            {
                "date": row.date,
                "precipitation": row.precipitation,
                "tmin": row.tmin,
                "tmax": row.tmax,
            }
            for row in cached_weather
        ]
    )
    accumulator = MetricAccumulatorService(weather_frame)
    print("Days since treatment:", accumulator.days_since("2026-04-01", "2026-04-10"))
    print("Rain since treatment:", accumulator.precipitation_since("2026-04-01", "2026-04-10"))
    print("GDD since treatment:", accumulator.gdd_since("2026-04-01", "2026-04-10", base_temperature=10))

    step("6. Create a crop protection rule", debug=args.debug)
    rule = db.crop_protection_service.create_rule(
        name="Debug scab cover",
        target="Apfelschorf",
        enabled=True,
        season_start=None,
        season_end=None,
        logic="any",
        notes="Debug-only example",
        product_names=["Delan 70 WG"],
        scopes=[{"scope_type": "section", "scope_id": section_id}],
        metrics=[
            {"metric_type": "days_since", "enabled": True, "threshold": 7, "warning_threshold": 5, "metric_config": {}},
            {"metric_type": "rain_since", "enabled": True, "threshold": 20, "warning_threshold": 15, "metric_config": {}},
            {
                "metric_type": "gdd_since",
                "enabled": True,
                "threshold": 80,
                "warning_threshold": 60,
                "metric_config": {"base_temperature": 10},
            },
        ],
    )
    print(f"Created rule_id={rule.id}, products={[product.product_name for product in rule.products]}")

    step("7. Fetch the rule from the repository", debug=args.debug)
    with db.session_scope() as session:
        fetched_rule = db.crop_protection.get_by_id(session, rule.id)
    rule_response = CropProtectionRuleRead.model_validate(fetched_rule)
    print(f"Fetched rule={rule_response.name}, metrics={[metric.metric_type for metric in rule_response.metrics]}")

    step("8. Evaluate crop protection status", debug=args.debug)
    evaluations = db.crop_protection_service.evaluate_rules(
        rule_id=rule.id,
        season_year=2026,
        as_of=datetime.date(2026, 4, 10),
    )
    for evaluation in evaluations:
        CropProtectionRuleEvaluationRead.model_validate(evaluation)
        print(
            f"{evaluation.field_name} / {evaluation.section_name}: status={evaluation.status}, "
            f"last={evaluation.last_treatment_date} {evaluation.last_treatment_product}"
        )
        for metric in evaluation.metrics:
            print(f"  - {metric.metric_type}: value={metric.value}, status={metric.status}")

    db.close()


if __name__ == "__main__":
    main()
