from __future__ import annotations

import time
from typing import Any

from seleniumbase import Driver

from .base import ScrapeResult


class SeleniumBaseScraper:
    name = "seleniumbase"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()
        driver = None

        try:
            driver = Driver(
                uc=True,
                headless=True,
            )

            driver.uc_open_with_reconnect(
                target["url"],
                reconnect_time=4,
            )

            html = driver.get_page_source() or ""
            title = driver.get_title()

            elapsed_ms = (time.perf_counter() - started) * 1000

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                provider_status_code=None,
                target_status_code=None,
                title=title,
                metadata={
                    "uc_mode": True,
                    "headless": True,
                    "reconnect_time": 4,
                },
            )

        except Exception as exc:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "uc_mode": True,
                    "headless": True,
                    "reconnect_time": 4,
                },
            )

        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
