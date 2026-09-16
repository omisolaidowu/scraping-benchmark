from __future__ import annotations

import time
from typing import Any

from seleniumbase import SB

from .base import ScrapeResult


class SeleniumBaseScraper:
    name = "seleniumbase"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        try:
            # UC Mode is SeleniumBase's undetected-chromedriver mode.
            # Keep the browser configuration fixed across benchmark targets.
            with SB(
                uc=True,
                headless=True,
            ) as sb:
                sb.uc_open_with_reconnect(
                    target["url"],
                    reconnect_time=4,
                )

                html = sb.get_page_source() or ""
                title = sb.get_title()

                elapsed_ms = (time.perf_counter() - started) * 1000

                return ScrapeResult(
                    approach=self.name,
                    target_id=target["id"],
                    url=target["url"],
                    success=bool(html),
                    elapsed_ms=elapsed_ms,
                    html=html,
                    status_code=None,
                    title=title,
                )

        except Exception as exc:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
            )
