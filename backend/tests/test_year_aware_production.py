import datetime as dt
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.application.production import ProductionSummaryService
from src.database import models
from src.database.db import Database


def _seed_replanted_field() -> tuple[Database, dict[str, int]]:
    db = Database("sqlite:///:memory:", initialize_schema=True)
    ids: dict[str, int] = {}

    with db.session_scope() as session:
        db.varieties.create(session, name="Old Variety", group="apple")
        db.varieties.create(session, name="New Variety", group="apple")
        field = db.fields.create(
            session,
            group="Test",
            name="Replanted",
            reference_provider="manual",
            reference_station="station",
            elevation=500,
        )
        old_planting = db.plantings.create(
            session,
            field_id=field.id,
            variety="Old Variety",
            valid_from=dt.date(2010, 1, 1),
            valid_to=dt.date(2020, 12, 31),
        )
        new_planting = db.plantings.create(
            session,
            field_id=field.id,
            variety="New Variety",
            valid_from=dt.date(2021, 1, 1),
        )
        old_section = db.sections.create(
            session,
            planting_id=old_planting.id,
            name="Old",
            planting_year=2010,
            area=10000,
            tree_count=100,
            valid_from=dt.date(2010, 1, 1),
            valid_to=dt.date(2020, 12, 31),
        )
        new_section = db.sections.create(
            session,
            planting_id=new_planting.id,
            name="New",
            planting_year=2021,
            area=20000,
            tree_count=200,
            valid_from=dt.date(2021, 1, 1),
        )
        ids.update(
            field=field.id,
            old_planting=old_planting.id,
            new_planting=new_planting.id,
            old_section=old_section.id,
            new_section=new_section.id,
        )

        db.yearly_stats.create(session, season_year=2020, field_id=field.id, yield_kg=1000)
        db.yearly_stats.create(session, season_year=2021, field_id=field.id, yield_kg=4000)

    return db, ids


def test_field_statistics_uses_selected_year_structure_for_replanted_fields():
    db, _ = _seed_replanted_field()
    try:
        service = ProductionSummaryService(db)

        stats_2020 = service.get_field_statistics(season_year=2020)
        assert [row["planting_name"] for row in stats_2020["rows"]] == ["Old Variety"]
        assert stats_2020["rows"][0]["area"] == 10000
        assert stats_2020["rows"][0]["tree_count"] == 100
        assert stats_2020["rows"][0]["metrics"]["yield_kg"]["value"] == 1000
        assert stats_2020["rows"][0]["metrics"]["yield_kg"]["value_per_hectare"] == 1000
        assert stats_2020["summary"]["area"] == 10000
        assert stats_2020["summary"]["metrics"]["yield_kg"]["value"] == 1000

        stats_2021 = service.get_field_statistics(season_year=2021)
        assert [row["planting_name"] for row in stats_2021["rows"]] == ["New Variety"]
        assert stats_2021["rows"][0]["area"] == 20000
        assert stats_2021["rows"][0]["tree_count"] == 200
        assert stats_2021["rows"][0]["metrics"]["yield_kg"]["value"] == 4000
        assert stats_2021["rows"][0]["metrics"]["yield_kg"]["value_per_hectare"] == 2000
        assert stats_2021["summary"]["area"] == 20000
        assert stats_2021["summary"]["metrics"]["yield_kg"]["value"] == 4000
    finally:
        db.close()


def test_scoped_yearly_stats_and_fruit_counts_reject_inactive_years():
    db, ids = _seed_replanted_field()
    try:
        with db.session_scope() as session:
            with pytest.raises(ValueError, match="Planting .* is not active in season_year 2020"):
                db.yearly_stats.create(
                    session,
                    season_year=2020,
                    planting_id=ids["new_planting"],
                    yield_kg=1,
                )

            with pytest.raises(ValueError, match="Planting .* is not active in season_year 2020"):
                db.fruit_counts.create(
                    session,
                    season_year=2020,
                    date=dt.date(2020, 6, 1),
                    timing_code="before",
                    planting_id=ids["new_planting"],
                    samples=[{"apple_count": 10}],
                )
    finally:
        db.close()


def test_scoped_yearly_stats_and_fruit_counts_filter_inactive_rows():
    db, ids = _seed_replanted_field()
    try:
        with db.session_scope() as session:
            session.add(models.YearlyStats(season_year=2020, planting_id=ids["new_planting"], yield_kg=999))
            session.add(
                models.FruitCountSurvey(
                    season_year=2020,
                    date=dt.date(2020, 6, 1),
                    timing_code="before",
                    planting_id=ids["new_planting"],
                    samples=[models.FruitCountSample(apple_count=99)],
                )
            )

        with db.session_scope() as session:
            yearly_stats = db.yearly_stats.list_for_field(
                session,
                field_id=ids["field"],
                season_years=[2020],
            )
            fruit_counts = db.fruit_counts.list_for_field(
                session,
                field_id=ids["field"],
                season_years=[2020],
            )

        assert [item.yield_kg for item in yearly_stats] == [1000]
        assert fruit_counts == []
    finally:
        db.close()
