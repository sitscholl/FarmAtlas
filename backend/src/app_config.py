import os
from pathlib import Path


DEFAULT_APP_CONFIG_PATH = Path("config/config.yaml")
DEFAULT_LOG_CONFIG_PATH = Path("config/config.logging.yaml")


def get_app_config_path() -> Path:
    return Path(os.getenv("FARMATLAS_CONFIG_PATH", str(DEFAULT_APP_CONFIG_PATH)))


def get_log_config_path() -> Path:
    return Path(os.getenv("FARMATLAS_LOG_CONFIG_PATH", str(DEFAULT_LOG_CONFIG_PATH)))
