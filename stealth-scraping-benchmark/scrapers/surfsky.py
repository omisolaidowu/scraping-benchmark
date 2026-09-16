from __future__ import annotations

import time
from contextlib import suppress
from typing import Any

from dotenv import load_dotenv
from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
from patchright.sync_api import sync_playwright
from surfsky import Surfsky

from .base import ScrapeResult

load_dotenv()

AUTO_CAPTCHA_TYPES = ["turnstile", "recaptcha", "datadome"]


class SurfskyScraper:
    """Surfsky cloud browser via Patchright/CDP with CAPTCHA solving."""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        self.client = Surfsky()
        self.timeout_seconds = timeout_seconds

    def _start_session(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "anti_captcha": {
                "enabled": True,
                "auto_captcha_types": AUTO_CAPTCHA_TYPES,
            },
            "browser_settings": {
                "inactive_kill_timeout": self.timeout_seconds + 10,
            },
        }

        response = self.client.request("POST", "/profiles/one_time", json=body)
        if response.is_error:
            raise RuntimeError(
                f"Session start failed: HTTP {response.status_code} - {response.text}"
            )

        return response.json()

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()
        captcha_events: list[dict[str, Any]] = []
        result = ScrapeResult(
            approach=self.name,
            target_id=target["id"],
            url=target["url"],
            success=False,
            elapsed_ms=0,
            metadata={
                "browser": "surfsky_cdp",
                "playwright_variant": "patchright",
                "anti_captcha": True,
                "auto_captcha_types": AUTO_CAPTCHA_TYPES,
                "captcha_events": captcha_events,
            },
        )
        internal_uuid: str | None = None

        try:
            session = self._start_session()
            internal_uuid = session["internal_uuid"]
            result.metadata["internal_uuid"] = internal_uuid

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(session["ws_url"])
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()

                cdp = context.new_cdp_session(page)
                for event in ("Captcha.solveCompleted", "Captcha.solveFailed"):
                    cdp.on(
                        event,
                        lambda params, event=event: captcha_events.append(
                            {"event": event, **params}
                        ),
                    )
                cdp.send("Captcha.autoSolve")

                try:
                    page.goto(
                        target["url"],
                        wait_until="domcontentloaded",
                        timeout=self.timeout_seconds * 1000,
                    )

                    remaining = started + self.timeout_seconds - time.perf_counter()
                    try:
                        page.wait_for_selector(
                            target["extraction"]["record_selector"],
                            state="attached",
                            timeout=max(remaining, 1) * 1000,
                        )
                    except PlaywrightTimeoutError:
                        pass

                    result.html = page.content()
                    result.title = page.title()
                    result.success = bool(result.html)

                finally:
                    result.elapsed_ms = (time.perf_counter() - started) * 1000

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.elapsed_ms = (
                result.elapsed_ms or (time.perf_counter() - started) * 1000
            )

        finally:
            if internal_uuid:
                with suppress(Exception):
                    self.client.profiles.stop(internal_uuid)

        return result
