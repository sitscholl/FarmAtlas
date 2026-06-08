from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://app.smartfarmer.it/#/auth/welcome/"
DEFAULT_SMARTFARMER_DIR = Path("var/smartfarmer")
DEFAULT_USER_DATA_SUBDIR = Path("browser-profile")
DEFAULT_DOWNLOADS_SUBDIR = Path("downloads")
DEFAULT_KEEP_DOWNLOADS = False
DEFAULT_HEADLESS = True
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 90
DEFAULT_REPORT_READY_DELAY_SECONDS = 0.0
DEFAULT_TIMEZONE_ID = "Europe/Rome"
DEFAULT_LOCALE = "de-DE"
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1400
DEFAULT_DISABLE_PASSWORD_MANAGER = True


def _path_or_none(value: str | Path | None, *, base_dir: Path | None = None) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    path = Path(value)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path


def _default_storage_dir(base_dir: Path | None) -> Path:
    if base_dir is None:
        return DEFAULT_SMARTFARMER_DIR
    return base_dir.parent / DEFAULT_SMARTFARMER_DIR


@dataclass(slots=True)
class SmartFarmerSettings:
    base_url: str = DEFAULT_BASE_URL
    username: str | None = None
    password: str | None = None
    user_data_dir: Path = DEFAULT_SMARTFARMER_DIR / DEFAULT_USER_DATA_SUBDIR
    downloads_dir: Path = DEFAULT_SMARTFARMER_DIR / DEFAULT_DOWNLOADS_SUBDIR
    keep_downloads: bool = DEFAULT_KEEP_DOWNLOADS
    headless: bool = DEFAULT_HEADLESS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    download_timeout_seconds: int = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS
    report_ready_delay_seconds: float = DEFAULT_REPORT_READY_DELAY_SECONDS
    timezone_id: str = DEFAULT_TIMEZONE_ID
    locale: str = DEFAULT_LOCALE
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT
    disable_password_manager: bool = DEFAULT_DISABLE_PASSWORD_MANAGER
    record_har_path: Path | None = None
    selectors: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any] | None,
        *,
        base_dir: Path | None = None,
    ) -> "SmartFarmerSettings":
        config = config or {}
        base_dir = base_dir.resolve() if base_dir is not None else None
        storage_dir = _default_storage_dir(base_dir)

        return cls(
            base_url=str(config.get("base_url", DEFAULT_BASE_URL)),
            username=config.get("username"),
            password=config.get("password"),
            user_data_dir=storage_dir / DEFAULT_USER_DATA_SUBDIR,
            downloads_dir=storage_dir / DEFAULT_DOWNLOADS_SUBDIR,
            keep_downloads=bool(config.get("keep_downloads", DEFAULT_KEEP_DOWNLOADS)),
            headless=bool(config.get("headless", DEFAULT_HEADLESS)),
            timeout_seconds=int(config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)),
            download_timeout_seconds=int(
                config.get("download_timeout_seconds", DEFAULT_DOWNLOAD_TIMEOUT_SECONDS)
            ),
            report_ready_delay_seconds=float(
                config.get("report_ready_delay_seconds", DEFAULT_REPORT_READY_DELAY_SECONDS)
            ),
            timezone_id=str(config.get("timezone_id", DEFAULT_TIMEZONE_ID)),
            locale=str(config.get("locale", DEFAULT_LOCALE)),
            viewport_width=int(config.get("viewport_width", DEFAULT_VIEWPORT_WIDTH)),
            viewport_height=int(config.get("viewport_height", DEFAULT_VIEWPORT_HEIGHT)),
            disable_password_manager=bool(
                config.get("disable_password_manager", DEFAULT_DISABLE_PASSWORD_MANAGER)
            ),
            record_har_path=_path_or_none(config.get("record_har_path"), base_dir=base_dir),
            selectors=dict(config.get("selectors") or {}),
        )

    def resolve_username(self) -> str | None:
        return self.username

    def resolve_password(self) -> str | None:
        return self.password
