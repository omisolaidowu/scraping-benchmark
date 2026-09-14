from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from dotenv import load_dotenv
from surfsky import AsyncSurfsky, BrowserSettings, BrowserTimeoutError

from .base import ScrapeResult

load_dotenv()


class SurfskyScraper:
    """Surfsky cloud browser driven over CDP by the surfsky-py SDK."""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        for var in ("SURFSKY_API_TOKEN", "SURFSKY_API_BASE_URL"):
            if not os.getenv(var):
                raise RuntimeError(f"{var} is not set")

        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        return asyncio.run(self._scrape(target))

    async def _scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()
        result = ScrapeResult(
            approach=self.name,
            target_id=target["id"],
            url=target["url"],
            success=False,
            elapsed_ms=0,
            metadata={"sdk": "surfsky-py", "wait_until": "domcontentloaded"},
        )

        try:
            async with (
                AsyncSurfsky() as client,
                client.browser(
                    browser_settings=BrowserSettings(
                        inactive_kill_timeout=self.timeout_seconds + 10,
                    ),
                ) as browser,
            ):
                result.metadata["internal_uuid"] = browser.internal_uuid

                try:
                    await browser.goto(
                        target["url"],
                        wait_until="domcontentloaded",
                        timeout=self.timeout_seconds,
                    )

                    remaining = started + self.timeout_seconds - time.perf_counter()
                    try:
                        await browser.wait_for_selector(
                            target["extraction"]["record_selector"],
                            visible=False,
                            timeout=max(remaining, 1),
                        )
                    except BrowserTimeoutError:
                        pass

                    result.html = await browser.content()
                    result.title = await browser.title()
                    result.target_status_code = browser.status
                    result.success = bool(result.html)

                finally:
                    result.elapsed_ms = (time.perf_counter() - started) * 1000

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.elapsed_ms = (
                result.elapsed_ms or (time.perf_counter() - started) * 1000
            )

        return result
