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

TOKEN = "(selector) => document.querySelector(selector)?.value || ''"


async def read_page(browser: Any) -> tuple[str, str]:
    for _ in range(5):
        try:
            return await browser.content(), await browser.title()
        except CDPError:
            await asyncio.sleep(2)
    return await browser.content(), await browser.title()


async def type_into(browser: Any, selector: str, text: str) -> None:
    await browser.evaluate("(s) => document.querySelector(s).focus()", selector)
    await browser.send("Input.insertText", {"text": text})


class SurfskyScraper:
    """Surfsky cloud browser through the surfsky-py SDK: a macOS fingerprint and
    the anti-captcha solver on auto-solve. A premium proxy only when the target
    sets `surfsky.proxy_country`"""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        return asyncio.run(self._scrape(target))

    async def _scrape(self, target: dict[str, Any]) -> ScrapeResult:
        country = (target.get("surfsky") or {}).get("proxy_country")
        proxy = {"proxy": PremiumProxy(country=country)} if country else {}
        captcha_events: list[dict[str, Any]] = []
        result = ScrapeResult(
            approach=self.name,
            target_id=target["id"],
            url=target["url"],
            success=False,
            elapsed_ms=0,
            metadata={
                "sdk": "surfsky-py",
                "proxy": f"premium:{country}" if country else "none",
                "fingerprint": "mac/x86",
                "anti_captcha": "auto_solve",
                "turnstile_login": True,
                "captcha_events": captcha_events,
            },
        )

        started = time.perf_counter()
        try:
            async with (
                AsyncSurfsky() as client,
                client.browser(
                    fingerprint=Fingerprint(os="mac", os_arch="x86"),
                    **proxy,
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
                    await browser.send("Captcha.autoSolve")
                    await browser.goto(
                        target["url"],
                        wait_until="domcontentloaded",
                        timeout=self.timeout_seconds,
                    )
                    await self._login(browser, target["interaction"])

                    result.html, result.title = await read_page(browser)
                    result.status_code = browser.status
                    result.success = bool(result.html)
                finally:
                    result.elapsed_ms = (time.perf_counter() - started) * 1000

        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.elapsed_ms = result.elapsed_ms or (time.perf_counter() - started) * 1000

        return result

    async def _login(self, browser: Any, form: dict[str, Any]) -> None:
        deadline = time.perf_counter() + 60
        while True:
            try:
                await browser.wait_for_function(
                    TOKEN, form["response_selector"], timeout=max(deadline - time.perf_counter(), 1)
                )
                break
            except CDPError:
                if time.perf_counter() > deadline:
                    raise
                await asyncio.sleep(1)

        await type_into(browser, form["email_selector"], form["email"])
        await type_into(browser, form["password_selector"], form["password"])

        await browser.click(form["submit_selector"])
        try:
            await browser.wait_for_url(form["success_url_contains"], timeout=10)
        except BrowserTimeoutError:
            with suppress(CDPError, BrowserTimeoutError):
                if await browser.count(form["submit_selector"]):
                    await browser.click(form["submit_selector"], timeout=5)
            await browser.wait_for_url(form["success_url_contains"], timeout=30)
        await browser.wait_for_selector(form["success_selector"], timeout=30)
