from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from surfsky import AsyncSurfsky, Browser

from .base import ScrapeResult

load_dotenv()

logger = logging.getLogger("surfsky")

VALUE = "(s) => document.querySelector(s)?.value ?? ''"
TOKEN = "(selector) => document.querySelector(selector)?.value || ''"
WIDGET_BOX = """(selector) => {
    const r = document.querySelector(selector)?.getBoundingClientRect();
    return r ? {x: r.x, y: r.y, w: r.width, h: r.height} : null;
}"""


class SurfskyScraper:
    """Surfsky cloud browser using the AsyncSurfsky Browser API."""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

        self.api_token = os.getenv("SURFSKY_API_TOKEN")
        if not self.api_token:
            raise RuntimeError("SURFSKY_API_TOKEN is not set in .env")

    async def _fill(
        self,
        page: Browser,
        selector: str,
        value: str,
        tag: str,
    ) -> None:
        for attempt in (1, 2, 3):
            await page.fill(selector, value)

            if (
                await page.evaluate(
                    VALUE,
                    selector,
                )
                == value
            ):
                return

            logger.warning(f"{tag}: {selector} still empty " f"after fill #{attempt}")

        raise RuntimeError(f"{selector} would not take its value")

    async def _solve_turnstile(
        self,
        page: Browser,
        interaction: dict[str, Any],
        tag: str,
    ) -> None:
        waf_selector = interaction["waf_selector"]
        response_selector = interaction["response_selector"]

        box = await page.evaluate(
            WIDGET_BOX,
            waf_selector,
        )

        if not box:
            logger.info(f"{tag}: no turnstile widget")
            return

        if await page.evaluate(
            TOKEN,
            response_selector,
        ):
            logger.info(f"{tag}: turnstile solved itself")
            return

        checkbox = min(
            box["h"] - 20,
            50,
        )

        await page.mouse.click(
            box["x"] + 10 + checkbox / 2,
            box["y"] + box["h"] / 2,
        )

        logger.info(f"{tag}: clicked turnstile, waiting for token")

        await page.wait_for_function(
            TOKEN,
            response_selector,
            timeout=60,
        )

    async def _turnstile_login(
        self,
        browser: Browser,
        target: dict[str, Any],
        tag: str,
    ) -> None:
        interaction = target["interaction"]

        waf_selector = interaction["waf_selector"]
        email_selector = interaction["email_selector"]
        password_selector = interaction["password_selector"]
        submit_selector = interaction["submit_selector"]
        response_selector = interaction["response_selector"]
        success_selector = interaction["success_selector"]
        success_url_contains = interaction["success_url_contains"]

        email = interaction["email"]
        password = interaction["password"]

        await browser.wait_for_selector(
            waf_selector,
            timeout=30,
        )

        await self._solve_turnstile(
            browser,
            interaction,
            tag,
        )

        await self._fill(
            browser,
            email_selector,
            email,
            tag,
        )

        await self._fill(
            browser,
            password_selector,
            password,
            tag,
        )

        token = await browser.evaluate(
            TOKEN,
            response_selector,
        )

        if not token:
            raise RuntimeError("form filled but turnstile left no token")

        await browser.click(
            submit_selector,
        )

        await browser.wait_for_url(
            success_url_contains,
            timeout=30,
        )

        await browser.wait_for_selector(
            success_selector,
            timeout=30,
        )

    async def _run(
        self,
        browser: Browser,
        target: dict[str, Any],
        index: int,
    ) -> ScrapeResult:
        started = time.perf_counter()

        tag = f"{target['id']}-" f"{index:02d}"

        try:
            await browser.goto(
                target["url"],
                timeout=self.timeout_seconds,
            )

            interaction = target.get("interaction")

            if interaction and interaction.get("type") == "turnstile_login":
                await self._turnstile_login(
                    browser,
                    target,
                    tag,
                )

            else:
                record_selector = target["extraction"]["record_selector"]

                await browser.wait_for_selector(
                    record_selector,
                    timeout=self.timeout_seconds,
                )

            html = await browser.content()
            title = await browser.title()

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                html=html,
                status_code=None,
                title=title,
                metadata={
                    "browser": "surfsky",
                    "turnstile_login": bool(
                        interaction and interaction.get("type") == "turnstile_login"
                    ),
                },
            )

        except Exception as exc:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                html="",
                status_code=None,
                title=None,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "browser": "surfsky",
                    "turnstile_login": bool(
                        interaction and interaction.get("type") == "turnstile_login"
                    ),
                },
            )

    async def _scrape_async(
        self,
        target: dict[str, Any],
    ) -> ScrapeResult:
        async with AsyncSurfsky(api_token=self.api_token) as client:

            outcomes = await client.map(
                lambda browser, index: self._run(
                    browser,
                    target,
                    index,
                ),
                range(1, 2),
                concurrency=1,
                browser_settings={
                    "inactive_kill_timeout": (self.timeout_seconds),
                },
            )

            if not outcomes:
                return ScrapeResult(
                    approach=self.name,
                    target_id=target["id"],
                    url=target["url"],
                    success=False,
                    elapsed_ms=0,
                    html="",
                    status_code=None,
                    title=None,
                    error="Surfsky returned no outcomes",
                )

            outcome = outcomes[0]

            if outcome.ok:
                return outcome.value

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=0,
                html="",
                status_code=None,
                title=None,
                error=f"FAILED: {outcome.error}",
            )

    def scrape(
        self,
        target: dict[str, Any],
    ) -> ScrapeResult:
        return asyncio.run(self._scrape_async(target))
