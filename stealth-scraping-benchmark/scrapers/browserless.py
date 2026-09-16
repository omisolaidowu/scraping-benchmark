from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from .base import ScrapeResult

load_dotenv()


class BrowserlessScraper:
    """Browserless BrowserQL stealth configuration."""

    name = "browserless_stealth"

    def __init__(self, timeout_seconds: int = 60):
        token = os.getenv("BROWSERLESS_API_TOKEN")

        if not token:
            raise RuntimeError("BROWSERLESS_API_TOKEN is not set")

        region = os.getenv(
            "BROWSERLESS_REGION",
            "production-sfo",
        )

        self.endpoint = f"https://{region}.browserless.io/stealth/bql"

        self.token = token
        self.timeout_seconds = timeout_seconds

    def _graphql_string(self, value: str) -> str:
        """Escape a Python string for a GraphQL string literal."""
        return (
            '"'
            + value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            + '"'
        )

    def _build_query(
        self,
        target: dict[str, Any],
    ) -> str:
        extraction = target["extraction"]

        url = target["url"]
        record_selector = extraction["record_selector"]

        return f"""
mutation Scrape {{
  goto(
    url: {self._graphql_string(url)}
    waitUntil: networkIdle
  ) {{
    status
    time
  }}

  records: waitForSelector(
    selector: {self._graphql_string(record_selector)}
    timeout: 60000
  ) {{
    time
  }}

  pageHtml: html {{
    html
  }}
}}
"""

    def scrape(
        self,
        target: dict[str, Any],
    ) -> ScrapeResult:
        started = time.perf_counter()

        try:
            query = self._build_query(target)

            response = requests.post(
                self.endpoint,
                params={
                    "token": self.token,
                    "proxy": "residential",
                    "humanlike": "true",
                    "proxyLocaleMatch": "1",
                },
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                json={
                    "query": query,
                    "variables": {},
                },
                timeout=self.timeout_seconds + 90,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000

            response.raise_for_status()

            payload = response.json()

            if payload.get("errors"):
                raise RuntimeError("BrowserQL returned errors: " f"{payload['errors']}")

            data = payload.get("data") or {}

            page_html_data = data.get("pageHtml") or {}

            html = page_html_data.get("html") or ""

            if not html:
                raise RuntimeError("Browserless returned no page HTML")

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                status_code=response.status_code,
                title=None,
                metadata={
                    "endpoint": "/stealth/bql",
                    "stealth": True,
                    "proxy": "residential",
                    "humanlike": True,
                    "proxy_locale_match": True,
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
                status_code=(response.status_code if "response" in locals() else None),
                title=None,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "endpoint": "/stealth/bql",
                    "stealth": True,
                    "proxy": "residential",
                    "humanlike": True,
                    "proxy_locale_match": True,
                },
            )
