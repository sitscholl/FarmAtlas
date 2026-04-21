import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from ..app_config import get_app_config_path

DEFAULT_DATABASE_URL = "sqlite:///db/database.db"


def load_config_from_path(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {config_path} must contain a top-level mapping.")
    return data


def get_database_url(config: Mapping[str, Any] | None = None) -> str:
    env_database_url = os.getenv("DATABASE_URL")
    if env_database_url:
        return env_database_url

    if config is None:
        config = load_config_from_path(get_app_config_path())

    database_config = config.get("database", {}) if isinstance(config, Mapping) else {}
    if isinstance(database_config, Mapping):
        database_url = database_config.get("path")
        if database_url:
            return str(database_url)

    return DEFAULT_DATABASE_URL
