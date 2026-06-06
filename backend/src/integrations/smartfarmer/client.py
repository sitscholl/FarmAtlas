from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
import time

from .config import SmartFarmerSettings
from .exceptions import SmartFarmerError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SmartFarmerDownloadedReport:
    content: bytes
    suggested_filename: str | None = None
    path: Path | None = None


class SmartFarmerClient:
    """Playwright-backed Smart Farmer client.

    Keep browser automation details contained here so a future HTTP client can
    expose the same fetch methods without changing Farm Atlas workflows.
    """

    def __init__(self, settings: SmartFarmerSettings) -> None:
        self.settings = settings
        self._playwright = None
        self._context = None
        self._page = None

    def __enter__(self) -> "SmartFarmerClient":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SmartFarmerError(
                "Playwright is not installed. Install backend dependencies and run "
                "'playwright install chromium' before using Smart Farmer fetching."
            ) from exc

        self.settings.user_data_dir.mkdir(parents=True, exist_ok=True)
        download_dir = self._download_dir()
        download_dir.mkdir(parents=True, exist_ok=True)
        if self.settings.record_har_path is not None:
            self.settings.record_har_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_chromium_preferences(download_dir)

        self._playwright = sync_playwright().start()
        launch_kwargs = {
            "headless": self.settings.headless,
            "accept_downloads": True,
            "timezone_id": self.settings.timezone_id,
            "locale": self.settings.locale,
            "viewport": {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            },
            "args": [
                f"--window-size={self.settings.viewport_width},{self.settings.viewport_height}",
                "--disable-infobars",
                "--disable-popup-blocking",
                "--disable-session-crashed-bubble",
                "--hide-crash-restore-bubble",
                "--no-default-browser-check",
                "--no-first-run",
                "--noerrdialogs",
            ],
        }
        if self.settings.disable_password_manager:
            launch_kwargs["args"].extend(
                [
                "--disable-features=PasswordManagerOnboarding,PasswordLeakDetection,AutofillServerCommunication",
                "--password-store=basic",
                ]
            )
        if download_dir is not None:
            launch_kwargs["downloads_path"] = str(download_dir)
        if self.settings.record_har_path is not None:
            launch_kwargs["record_har_path"] = str(self.settings.record_har_path)

        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.settings.user_data_dir),
            **launch_kwargs,
        )
        self._context.set_default_timeout(self.settings.timeout_seconds * 1000)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.set_viewport_size(
            {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height,
            }
        )
        self._configure_download_behavior(download_dir)
        return self

    def _download_dir(self) -> Path:
        return self.settings.downloads_dir or self.settings.user_data_dir / "Downloads"

    def _write_chromium_preferences(self, download_dir: Path) -> None:
        preferences_path = self.settings.user_data_dir / "Default" / "Preferences"
        preferences_path.parent.mkdir(parents=True, exist_ok=True)
        preferences = {}
        if preferences_path.exists():
            try:
                preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Could not parse Chromium preferences at %s", preferences_path)

        download_preferences = preferences.setdefault("download", {})
        if isinstance(download_preferences, dict):
            download_preferences["default_directory"] = str(download_dir.resolve())
            download_preferences["directory_upgrade"] = True
            download_preferences["prompt_for_download"] = False

        safebrowsing_preferences = preferences.setdefault("safebrowsing", {})
        if isinstance(safebrowsing_preferences, dict):
            safebrowsing_preferences["enabled"] = True

        profile_preferences = preferences.setdefault("profile", {})
        if isinstance(profile_preferences, dict):
            profile_preferences["exited_cleanly"] = True
            profile_preferences["exit_type"] = "Normal"
            profile_preferences["default_content_setting_values"] = {
                **profile_preferences.get("default_content_setting_values", {}),
                "automatic_downloads": 1,
            }
            if self.settings.disable_password_manager:
                profile_preferences["password_manager_enabled"] = False

        if self.settings.disable_password_manager:
            preferences["credentials_enable_service"] = False
            preferences.setdefault("password_manager", {})["enabled"] = False

        preferences_path.write_text(
            json.dumps(preferences, separators=(",", ":")),
            encoding="utf-8",
        )

    def _configure_download_behavior(self, download_dir: Path) -> None:
        if self._context is None or self._page is None:
            return
        try:
            cdp_session = self._context.new_cdp_session(self._page)
            cdp_session.send(
                "Page.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": str(download_dir.resolve()),
                },
            )
        except Exception as exc:
            logger.debug("Could not configure Chromium download behavior: %s", exc)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._page = None

    @property
    def page(self):
        if self._page is None:
            raise SmartFarmerError("Smart Farmer client is not open.")
        return self._page

    def fetch_treatment_report(self, season_year: int) -> SmartFarmerDownloadedReport:
        self._login_if_required()
        self._close_known_popups()
        self._navigate_to_treatment_report(season_year)
        return self._download_treatment_report(season_year)

    def _login_if_required(self) -> None:
        page = self.page
        logger.info("Opening Smart Farmer")
        page.goto(self.settings.base_url, wait_until="domcontentloaded")

        state, locator = self._wait_for_first_visible(
            [
                ("login", page.locator('input[type="email"]')),
                ("dashboard", page.get_by_role("button", name=re.compile(r"Berichte", re.IGNORECASE))),
                ("popup", page.get_by_role("button", name=re.compile(r"sp.ter", re.IGNORECASE))),
                ("popup", page.get_by_role("button", name=re.compile(r"jetzt nicht", re.IGNORECASE))),
            ],
            description="Smart Farmer login form, dashboard, or popup",
            timeout_ms=self.settings.timeout_seconds * 1000,
        )
        if state != "login":
            logger.info("Smart Farmer login form not visible; using persisted session")
            return

        username = self.settings.resolve_username()
        password = self.settings.resolve_password()
        if not username or not password:
            raise SmartFarmerError(
                "Smart Farmer login is required but username/password are missing."
            )

        logger.info("Logging into Smart Farmer")
        locator.fill(username)
        self._click_first(
            [
                page.get_by_role("button", name=re.compile(r"weiter", re.IGNORECASE)),
                page.locator('button:has-text("weiter")'),
            ],
            description="Smart Farmer email continue button",
        )
        password_input = page.locator('input[type="password"]').first
        password_input.wait_for(state="visible", timeout=self.settings.timeout_seconds * 1000)
        password_input.fill(password)
        self._click_first(
            [
                page.get_by_role("button", name=re.compile(r"login", re.IGNORECASE)),
                page.locator('button:has-text("login")'),
            ],
            description="Smart Farmer login button",
        )
        self._wait_for_dashboard()

    def _wait_for_dashboard(self) -> None:
        self._wait_for_first_visible(
            [
                ("dashboard", self.page.get_by_role("button", name=re.compile(r"Berichte", re.IGNORECASE))),
                ("popup", self.page.get_by_role("button", name=re.compile(r"sp.ter", re.IGNORECASE))),
                ("popup", self.page.get_by_role("button", name=re.compile(r"jetzt nicht", re.IGNORECASE))),
            ],
            description="Smart Farmer dashboard or popup",
            timeout_ms=30_000,
        )

    def _close_known_popups(self) -> None:
        for label in (r"sp.ter", r"jetzt nicht"):
            locator = self.page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
            try:
                if locator.count() > 0 and locator.first.is_visible(timeout=1_000):
                    locator.first.click(timeout=1_000)
            except Exception:
                logger.debug("Smart Farmer popup button %s was not clickable", label)

    def _navigate_to_treatment_report(self, season_year: int) -> None:
        page = self.page
        logger.info("Navigating to Smart Farmer treatment report for %s", season_year)
        self._click_first(
            [
                page.get_by_role("button", name=re.compile(r"Berichte", re.IGNORECASE)),
                page.locator('button:has-text("Berichte")'),
            ],
            description="Smart Farmer Berichte button",
        )
        self._click_first(
            [
                page.get_by_text(re.compile(r"Ma.nahmen|Massnahmen", re.IGNORECASE)),
                page.locator('text=/Ma.nahmen|Massnahmen/i'),
            ],
            description="Smart Farmer Massnahmen menu item",
        )
        self._click_first(
            [
                page.get_by_text("Liste", exact=True),
                page.locator('text="Liste"'),
            ],
            description="Smart Farmer Liste menu item",
        )
        self._close_known_popups()

        self._click_first(
            [
                page.locator('span:has-text("Erntejahr")'),
                page.locator('span:has-text("Kalenderjahr")'),
            ],
            description="Smart Farmer year dropdown",
        )
        self._click_first(
            [
                page.get_by_text(f"Kalenderjahr {season_year}", exact=True),
                page.locator(f'text="Kalenderjahr {season_year}"'),
            ],
            description=f"Smart Farmer Kalenderjahr {season_year} option",
        )
        self._wait_for_treatment_report_ready(season_year)

    def _wait_for_treatment_report_ready(self, season_year: int) -> None:
        logger.info("Waiting for Smart Farmer treatment report %s to render", season_year)
        candidates = [
            ("empty", self.page.get_by_text(re.compile(r"Keine passenden Eintr.ge gefunden", re.IGNORECASE))),
            *[("download", locator) for locator in self._treatment_download_button_candidates()],
            ("table", self.page.locator("table, [role='table'], [role='grid']").first),
        ]

        self._wait_for_first_visible(
            candidates,
            description=f"Smart Farmer treatment report for {season_year}",
            timeout_ms=45_000,
        )

    def _download_treatment_report(self, season_year: int) -> SmartFarmerDownloadedReport:
        if re.search(r"Keine passenden Eintr.ge gefunden", self.page.content()):
            raise SmartFarmerError(f"Smart Farmer contains no treatment rows for {season_year}.")

        candidates = self._treatment_download_button_candidates()

        logger.info("Downloading Smart Farmer treatment report for %s", season_year)
        try:
            with self.page.expect_download(timeout=self.settings.download_timeout_seconds * 1000) as download_info:
                self._click_first(candidates, description="Smart Farmer treatment report download button")
            download = download_info.value
            failure = download.failure()
            if failure:
                raise SmartFarmerError(
                    "Smart Farmer treatment report download failed in Chromium: "
                    f"{failure}; suggested_filename={download.suggested_filename!r}"
                )
            path, content = self._read_download_content(download)

            if (
                self.settings.keep_downloads
                and self.settings.downloads_dir is not None
                and download.suggested_filename
            ):
                target = self.settings.downloads_dir / download.suggested_filename
                if path != target:
                    download.save_as(str(target))
                    path = target
                logger.info("Saved Smart Farmer download to %s", path)
            elif not self.settings.keep_downloads:
                self._cleanup_download_files(download, path)
                path = None

            return SmartFarmerDownloadedReport(
                content=content,
                suggested_filename=download.suggested_filename,
                path=path,
            )
        except SmartFarmerError:
            raise
        except Exception as exc:
            raise SmartFarmerError(f"Could not download Smart Farmer treatment report: {exc}") from exc

    def _read_download_content(self, download) -> tuple[Path, bytes]:
        artifact_path = Path(download.path())
        if artifact_path.exists() and artifact_path.is_file():
            return artifact_path, artifact_path.read_bytes()

        suggested_filename = download.suggested_filename
        if suggested_filename:
            named_path = self._download_dir() / suggested_filename
            if named_path.exists() and named_path.is_file():
                return named_path, named_path.read_bytes()

        raise SmartFarmerError(
            "Smart Farmer treatment report download completed, but the file could not be read. "
            f"artifact_path={artifact_path}, suggested_filename={suggested_filename!r}"
        )

    def _cleanup_download_files(self, download, path: Path | None) -> None:
        candidates: list[Path] = []
        if path is not None:
            candidates.append(path)

        try:
            artifact_path = Path(download.path())
            candidates.append(artifact_path)
        except Exception:
            pass

        suggested_filename = download.suggested_filename
        if suggested_filename:
            candidates.append(self._download_dir() / suggested_filename)

        for candidate in {item.resolve() for item in candidates if item is not None}:
            try:
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()
                    logger.debug("Deleted temporary Smart Farmer download %s", candidate)
            except OSError as exc:
                logger.warning("Could not delete temporary Smart Farmer download %s: %s", candidate, exc)

    def _treatment_download_button_candidates(self):
        selector = self.settings.selectors.get("treatment_report_download_button")
        candidates = []
        if selector:
            candidates.append(self.page.locator(selector))
        candidates.extend(
            [
                self.page.locator(
                    "xpath=/html/body/div[1]/div/div[1]/div[1]/div[1]/div/div[2]/div/div[2]/div/div/div[1]/span[2]/span/button[2]"
                ),
                self.page.locator('button[title*="Download" i]'),
                self.page.locator('button[title*="Export" i]'),
                self.page.get_by_role("button", name=re.compile(r"download|export", re.IGNORECASE)),
            ]
        )
        return candidates

    def _wait_for_first_visible(
        self,
        candidates,
        *,
        description: str,
        timeout_ms: int,
    ):
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            for name, locator in candidates:
                try:
                    if locator.count() > 0 and locator.first.is_visible():
                        return name, locator.first
                except Exception:
                    continue
            self.page.wait_for_timeout(250)
        raise SmartFarmerError(f"Could not find {description}.")

    def _click_first(self, locators, *, description: str) -> None:
        timeout = min(self.settings.timeout_seconds * 1000, 5_000)
        last_error: Exception | None = None
        for locator in locators:
            target = locator.first
            try:
                target.scroll_into_view_if_needed(timeout=timeout)
                target.click(timeout=timeout)
                return
            except Exception as exc:
                last_error = exc

            try:
                target.evaluate("(element) => element.click()")
                return
            except Exception as exc:
                last_error = exc
                continue
        detail = "" if last_error is None else f" Last error: {last_error}"
        raise SmartFarmerError(f"Could not click {description}.{detail}")
