from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.integrations.smartfarmer import (
    SmartFarmerClient,
    SmartFarmerSettings,
    read_treatment_export,
)
from src.runtime import RuntimeContext, load_config_file


BACKEND_DIR = Path(__file__).resolve().parents[1]


def step(title: str, *, debug: bool, pause: bool) -> None:
    print(f"\n=== {title} ===")
    if debug:
        breakpoint()
    if pause:
        input("Press Enter to continue...")


def build_settings(args) -> SmartFarmerSettings:
    config = load_config_file(args.config)
    settings = SmartFarmerSettings.from_config(
        config.get("integrations", {}).get("smartfarmer", {}),
        base_dir=args.config.parent,
    )

    overrides = {}
    if args.show_browser:
        overrides["headless"] = False
    if args.headless:
        overrides["headless"] = True
    if args.user_data_dir is not None:
        overrides["user_data_dir"] = args.user_data_dir.resolve()
    if args.downloads_dir is not None:
        overrides["downloads_dir"] = args.downloads_dir.resolve()
    if args.har is not None:
        overrides["record_har_path"] = args.har.resolve()
    if args.keep_downloads:
        overrides["keep_downloads"] = True
    if args.timeout_seconds is not None:
        overrides["timeout_seconds"] = args.timeout_seconds
    if args.download_timeout_seconds is not None:
        overrides["download_timeout_seconds"] = args.download_timeout_seconds

    return replace(settings, **overrides)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and inspect a Smart Farmer treatment export with Playwright."
    )
    parser.add_argument("--config", type=Path, default=BACKEND_DIR / "config" / "config.yaml")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source", default="smartfarmer")
    parser.add_argument("--persist", action="store_true", help="Import parsed rows into the configured DB.")
    parser.add_argument("--output", type=Path, default=None, help="Optional path for saving the raw export bytes.")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible browser window.")
    parser.add_argument("--headless", action="store_true", help="Force headless mode.")
    parser.add_argument("--debug", action="store_true", help="Open breakpoint() at each step.")
    parser.add_argument("--pause", action="store_true", help="Wait for Enter at each step.")
    parser.add_argument("--har", type=Path, default=None, help="Optional HAR path for request inspection.")
    parser.add_argument("--user-data-dir", type=Path, default=None)
    parser.add_argument("--downloads-dir", type=Path, default=None)
    parser.add_argument("--keep-downloads", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--download-timeout-seconds", type=int, default=None)
    args = parser.parse_args()
    args.config = args.config.resolve()

    step("1. Load Smart Farmer settings", debug=args.debug, pause=args.pause)
    settings = build_settings(args)
    print(f"user_data_dir={settings.user_data_dir}")
    print(f"downloads_dir={settings.downloads_dir}")
    print(f"headless={settings.headless}")
    print(f"record_har_path={settings.record_har_path}")

    step("2. Open browser and download treatment export", debug=args.debug, pause=args.pause)
    with SmartFarmerClient(settings) as client:
        report = client.fetch_treatment_report(args.year)
    print(f"downloaded filename={report.suggested_filename}")
    print(f"downloaded path={report.path}")
    print(f"downloaded bytes={len(report.content)}")

    if args.output is not None:
        step("3. Save raw export bytes", debug=args.debug, pause=args.pause)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(report.content)
        print(f"saved={args.output.resolve()}")
    else:
        step("3. Skip saving raw export bytes", debug=args.debug, pause=args.pause)

    step("4. Parse export", debug=args.debug, pause=args.pause)
    dataframe = read_treatment_export(report.content, filename=report.suggested_filename)
    print(f"shape={dataframe.shape}")
    print(f"columns={list(dataframe.columns)}")
    print(dataframe.head(10).to_string(index=False))

    if not args.persist:
        print("\nNot importing into DB. Pass --persist to store TreatmentEvent rows.")
        return

    step("5. Import parsed export into configured DB", debug=args.debug, pause=args.pause)
    runtime = RuntimeContext.from_config_file(args.config)
    summary = runtime.db.treatment_import_service.import_full_season_dataframe(
        dataframe=dataframe,
        season_year=args.year,
        source=args.source,
    )
    print(
        f"imported rows={summary.row_count}, unresolved={summary.unresolved_count}, "
        f"source={summary.source}, season_year={summary.season_year}"
    )
    runtime.db.close()


if __name__ == "__main__":
    main()
