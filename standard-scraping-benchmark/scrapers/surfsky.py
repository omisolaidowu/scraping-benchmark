from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from typing import Any

from dotenv import load_dotenv
from surfsky import (
    AntiCaptcha,
    AsyncSurfsky,
    BrowserSettings,
    BrowserTimeoutError,
    CDPError,
    Fingerprint,
    PremiumProxy,
)

from .base import ScrapeResult

load_dotenv()


async def read_page(browser: Any) -> tuple[str, str]:
    for _ in range(5):
        try:
            return await browser.content(), await browser.title()
        except CDPError:
            await asyncio.sleep(2)
    return await browser.content(), await browser.title()


class SurfskyScraper:
    """Surfsky cloud browser through the surfsky-py SDK"""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        return asyncio.run(self._scrape(target))

    async def _scrape(self, target: dict[str, Any]) -> ScrapeResult:
        country = (target.get("surfsky") or {}).get("proxy_country", "us")
        captcha_events: list[dict[str, Any]] = []
        result = ScrapeResult(
            approach=self.name,
            target_id=target["id"],
            url=target["url"],
            success=False,
            elapsed_ms=0,
            metadata={
                "sdk": "surfsky-py",
                "proxy": f"premium:{country}",
                "fingerprint": "mac/x86",
                "anti_captcha": "auto_solve",
                "captcha_events": captcha_events,
            },
        )

        started = time.perf_counter()
        try:
            async with (
                AsyncSurfsky() as client,
                client.browser(
                    fingerprint=Fingerprint(os="mac", os_arch="x86"),
                    proxy=PremiumProxy(country=country),
                    anti_captcha=AntiCaptcha(enabled=True),
                    browser_settings=BrowserSettings(
                        inactive_kill_timeout=self.timeout_seconds + 30,
                    ),
                    command_timeout=90,
                ) as browser,
            ):
                result.metadata["internal_uuid"] = browser.internal_uuid
                for event in ("Captcha.solveCompleted", "Captcha.solveFailed"):
                    browser.cdp.on(
                        event,
                        lambda params, _sid, event=event: captcha_events.append(
                            {"event": event, "type": params.get("type"), "status": params.get("status")}
                        ),
                    )
                try:
                    # Solve any captcha the target shows from here on.
                    await browser.send("Captcha.autoSolve")
                    await browser.goto(
                        target["url"],
                        wait_until="domcontentloaded",
                        timeout=self.timeout_seconds,
                    )
                    remaining = started + self.timeout_seconds - time.perf_counter()
                    with suppress(BrowserTimeoutError):
                        await browser.wait_for_selector(
                            target["extraction"]["record_selector"],
                            visible=False,
                            timeout=max(remaining, 1),
                        )

                    result.html, result.title = await read_page(browser)
                    result.target_status_code = browser.status
                    result.success = bool(result.html)
                finally:
                    result.elapsed_ms = (time.perf_counter() - started) * 1000

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.elapsed_ms = result.elapsed_ms or (time.perf_counter() - started) * 1000

        return result
