from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from .base import ScrapeResult

load_dotenv()


class FirecrawlScraper:
    name = "firecrawl"
    API_URL = "https://api.firecrawl.dev/v2/scrape"

    def __init__(self, timeout_seconds: int = 60):
        api_key = os.getenv("FIRECRAWL_API_KEY")

        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is not set")

        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        payload = {
            "url": target["url"],
            "formats": ["rawHtml"],
            "onlyMainContent": False,
            "storeInCache": False,
            "timeout": self.timeout_seconds * 1000,
            "proxy": "auto",
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds + 10,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000

            try:
                body = response.json()
            except ValueError:
                body = {}

            data = body.get("data") or {}
            metadata = data.get("metadata") or {}

            html = data.get("rawHtml") or ""

            target_status_code = metadata.get("statusCode") or metadata.get(
                "pageStatusCode"
            )

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=response.ok,
                elapsed_ms=elapsed_ms,
                html=html,
                provider_status_code=response.status_code,
                target_status_code=target_status_code,
                title=metadata.get("title"),
                error=body.get("error"),
                metadata=metadata,
            )

        except requests.RequestException as exc:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
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
