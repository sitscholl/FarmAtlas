import datetime as dt
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.database.db import Database
from src.domain.field import FieldContext


def test_current_field_aggregates_use_active_sections_only():
    db = Database("sqlite:///:memory:", initialize_schema=True)
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)

    try:
        with db.session_scope() as session:
            db.varieties.create(session, name="Old Variety", group="apple")
            db.varieties.create(session, name="Current Variety", group="apple")
            field = db.fields.create(
                session,
                group="Test",
                name="Active Aggregates",
                reference_provider="manual",
                reference_station="station",
                elevation=500,
            )
            old_planting = db.plantings.create(
                session,
                field_id=field.id,
                variety="Old Variety",
                valid_from=dt.date(2010, 1, 1),
                valid_to=yesterday,
            )
            current_planting = db.plantings.create(
                session,
                field_id=field.id,
                variety="Current Variety",
                valid_from=today,
            )
            db.sections.create(
                session,
                planting_id=old_planting.id,
                name="Old",
                planting_year=2010,
                area=10000,
                tree_count=100,
                running_metre=1000,
                valid_from=dt.date(2010, 1, 1),
                valid_to=yesterday,
            )
            db.sections.create(
                session,
                planting_id=current_planting.id,
                name="Current",
                planting_year=today.year,
                area=2500,
                tree_count=25,
                running_metre=250,
                valid_from=today,
            )

            session.flush()
            session.expire_all()
            field = db.fields.get_by_id(session, field.id)
            assert field is not None

            assert field.area == 2500
            assert field.tree_count == 25
            assert field.running_metre == 250

            context = FieldContext.from_model(field)
            assert context.area == 2500
            assert context.tree_count == 25
            assert context.running_metre == 250
            assert context.variety == "Current Variety"
            assert context.section == "Current"
            assert context.planting_year == today.year
            assert [section.name for section in context.active_sections] == ["Current"]
    finally:
        db.close()
