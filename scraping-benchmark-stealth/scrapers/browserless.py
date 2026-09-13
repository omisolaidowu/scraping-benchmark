from __future__ import annotations

import os
import time
from typing import Any

import requests

from .base import ScrapeResult

from dotenv import load_dotenv

load_dotenv()


class BrowserlessScraper:
    """Browserless REST /unblock with explicit stealth + residential proxy."""

    name = "browserless_stealth"

    def __init__(self, timeout_seconds: int = 60):
        token = os.getenv("BROWSERLESS_API_TOKEN")
        if not token:
            raise RuntimeError("BROWSERLESS_API_TOKEN is not set")

        region = os.getenv("BROWSERLESS_REGION", "production-sfo")
        self.endpoint = f"https://{region}.browserless.io/unblock"
        self.token = token
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        try:
            response = requests.post(
                self.endpoint,
                params={
                    "token": self.token,
                    "proxy": "residential",
                    "stealth": "true",
                },
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "url": target["url"],
                    "content": True,
                    "cookies": False,
                    "screenshot": False,
                    "browserWSEndpoint": False,
                },
                timeout=self.timeout_seconds,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            payload = response.json()
            html = payload.get("content") or ""

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                status_code=response.status_code,
                metadata={
                    "endpoint": "/unblock",
                    "stealth": True,
                    "proxy": "residential",
                },
            )

        except Exception as exc:
            status_code = None
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                status_code = exc.response.status_code

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                status_code=status_code,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "endpoint": "/unblock",
                    "stealth": True,
                    "proxy": "residential",
                },
            )
