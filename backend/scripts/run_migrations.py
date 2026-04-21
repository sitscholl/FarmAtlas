from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.database.settings import get_database_url

BASELINE_REVISION = "0001_initial_schema"


def main() -> None:
    database_url = get_database_url()
    engine = create_engine(database_url, future=True)

    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    engine.dispose()

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    if not table_names:
        command.upgrade(alembic_config, "head")
        return

    if "alembic_version" in table_names:
        command.upgrade(alembic_config, "head")
        return

    raise SystemExit(
        "Database already contains tables but is not versioned by Alembic.\n"
        "Back up the database, then run:\n"
        f"  alembic stamp {BASELINE_REVISION}\n"
        "If the existing schema does not match the current models, create a dedicated baseline migration instead."
    )


if __name__ == "__main__":
    main()
