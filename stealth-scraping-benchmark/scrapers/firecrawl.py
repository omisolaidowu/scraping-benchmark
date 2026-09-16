from __future__ import annotations

import os
import time
from typing import Any

from firecrawl import Firecrawl

from .base import ScrapeResult

from dotenv import load_dotenv

load_dotenv()


class FirecrawlScraper:
    """Firecrawl enhanced-proxy configuration.

    Firecrawl's current Scrape API exposes proxy strategies rather than a
    browser-level stealth switch. The documented enhanced proxy is the
    provider's higher-resistance configuration for advanced anti-bot sites.
    """

    name = "firecrawl_stealth"

    def __init__(self, timeout_seconds: int = 60):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is not set")
        self.client = Firecrawl(api_key=api_key)
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        try:
            result = self.client.scrape(
                target["url"],
                formats=["html"],
                proxy="enhanced",
                store_in_cache=False,
                timeout=self.timeout_seconds * 1000,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000
            html = getattr(result, "html", None) or ""

            metadata = getattr(result, "metadata", None)
            metadata_dict: dict[str, Any] = {}
            if metadata is not None:
                if hasattr(metadata, "model_dump"):
                    metadata_dict = metadata.model_dump()
                elif isinstance(metadata, dict):
                    metadata_dict = metadata
                else:
                    metadata_dict = {
                        k: v for k, v in vars(metadata).items() if not k.startswith("_")
                    }

            status_code = metadata_dict.get("statusCode") or metadata_dict.get(
                "pageStatusCode"
            )

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                status_code=status_code,
                title=metadata_dict.get("title"),
                metadata={
                    **metadata_dict,
                    "stealth_config": "enhanced_proxy",
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
                metadata={"stealth_config": "enhanced_proxy"},
            )
