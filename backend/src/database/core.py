import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from . import models

logger = logging.getLogger(__name__)


def ensure_sqlite_directory(engine_url: str) -> None:
    if not engine_url.startswith("sqlite:///") or engine_url == "sqlite:///:memory:":
        return

    sqlite_path = engine_url.removeprefix("sqlite:///")
    if not sqlite_path:
        return

    database_path = Path(sqlite_path)
    parent_dir = database_path.parent
    if str(parent_dir) not in ("", "."):
        parent_dir.mkdir(parents=True, exist_ok=True)


class DatabaseCore:
    def __init__(self, engine_url: str = "sqlite:///db/database.db", **engine_kwargs) -> None:
        ensure_sqlite_directory(engine_url)
        self.engine: Engine = create_engine(engine_url, future=True, **engine_kwargs)
        models.Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
            logger.debug("Database engine disposed.")
