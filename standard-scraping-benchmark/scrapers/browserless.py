from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from .base import ScrapeResult

load_dotenv()


class BrowserlessScraper:
    name = "browserless"

    def __init__(self, timeout_seconds: int = 60):
        token = os.getenv("BROWSERLESS_API_TOKEN")

        if not token:
            raise RuntimeError("BROWSERLESS_API_TOKEN is not set")

        region = os.getenv("BROWSERLESS_REGION", "production-sfo")

        self.base_url = f"https://{region}.browserless.io"
        self.token = token
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        browserless_config = target.get("browserless") or {}

        endpoint_type = browserless_config.get("endpoint", "content")
        proxy = browserless_config.get("proxy")

        if endpoint_type not in {"content", "unblock"}:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=(
                    f"Unsupported Browserless endpoint: "
                    f"{endpoint_type!r}. Expected 'content' or 'unblock'."
                ),
            )

        endpoint = f"{self.base_url}/{endpoint_type}"

        params = {
            "token": self.token,
        }

        if proxy:
            params["proxy"] = proxy

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

        payload = {
            "url": target["url"],
        }

        # /unblock supports additional options.
        if endpoint_type == "unblock":
            payload.update(
                {
                    "content": True,
                    "cookies": False,
                    "screenshot": False,
                    "browserWSEndpoint": False,
                }
            )

        try:
            response = requests.post(
                endpoint,
                params=params,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000

            html = self._extract_content(response)

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=response.ok,
                elapsed_ms=elapsed_ms,
                html=html,
                provider_status_code=response.status_code,
                target_status_code=None,
                error=(None if response.ok else self._extract_error(response)),
                metadata={
                    "endpoint": endpoint_type,
                    "proxy": proxy,
                    "content_type": response.headers.get("content-type"),
                },
            )

        except requests.RequestException as exc:
            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "endpoint": endpoint_type,
                    "proxy": proxy,
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
                    "endpoint": endpoint_type,
                    "proxy": proxy,
                },
            )

    @staticmethod
    def _extract_content(response: requests.Response) -> str:
        """
        Extract HTML content from the Browserless response.

        Browserless endpoints may return JSON containing the
        rendered HTML in a `content` field. If the response is
        not JSON, fall back to the raw response body.
        """

        try:
            body = response.json()

            if isinstance(body, dict):
                content = body.get("content")

                if isinstance(content, str):
                    return content

        except ValueError:
            pass

        return response.text or ""

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        try:
            body = response.json()

            if isinstance(body, dict):
                error = body.get("error") or body.get("message")

                if error:
                    return str(error)

        except ValueError:
            pass

        return response.text.strip() or f"HTTP {response.status_code}"
