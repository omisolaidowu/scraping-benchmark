from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from .base import ScrapeResult

load_dotenv()


class SurfskyScraper:
    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        token = os.getenv("SURFSKY_API_TOKEN")
        base_url = os.getenv("SURFSKY_API_BASE_URL")

        if not token:
            raise RuntimeError("SURFSKY_API_TOKEN is not set")

        if not base_url:
            raise RuntimeError("SURFSKY_API_BASE_URL is not set")

        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Cloud-Api-Token": self.token,
        }

    def _create_profile(self) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/profiles/one_time",
            headers=self.headers,
            json={"anti_captcha": {"enabled": True}},
            timeout=self.timeout_seconds,
        )

        try:
            body = response.json()
        except ValueError:
            body = {}

        if not response.ok:
            raise RuntimeError(
                f"Profile creation failed: "
                f"HTTP {response.status_code} - "
                f"{body or response.text}"
            )

        return body

    def _stop_profile(self, profile_uuid: str) -> None:
        try:
            requests.post(
                f"{self.base_url}/profiles/{profile_uuid}/stop",
                headers=self.headers,
                timeout=10,
            )
        except requests.RequestException:
            # Cleanup failure should not replace the actual scrape result.
            pass

    @staticmethod
    def _extract_error(response: requests.Response) -> str:
        try:
            body = response.json()
            return str(body)
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()
        profile_uuid: str | None = None

        try:
            # Start a fresh one-time browser session.
            # CAPTCHA solving is enabled at browser start.
            profile = self._create_profile()

            profile_uuid = profile.get("internal_uuid")

            if not profile_uuid:
                raise RuntimeError(
                    "Surfsky profile response did not contain "
                    f"'internal_uuid': {profile}"
                )

            endpoint = f"{self.base_url}/profiles/" f"{profile_uuid}/scrape"

            payload = {
                "url": target["url"],
                "wait_until": "domcontentloaded",
                "timeout": self.timeout_seconds * 1000,
                "wait": 0,
                "screenshot": False,
                "auto_captcha_solve": True,
                "human_actions": 0,
            }

            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=self.timeout_seconds + 10,
            )

            elapsed_ms = (time.perf_counter() - started) * 1000

            try:
                body = response.json()
            except ValueError:
                body = {}

            data = body.get("data") or {}

            html = data.get("content") or ""

            target_status_code = data.get("status")

            error = None if response.ok else self._extract_error(response)

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=response.ok and bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                provider_status_code=response.status_code,
                target_status_code=target_status_code,
                error=error,
                metadata={
                    "profile_uuid": profile_uuid,
                    "cookies_present": bool(data.get("cookies")),
                    "screenshot_requested": False,
                    "wait_until": "domcontentloaded",
                    "wait": 0,
                    "auto_captcha_solve": True,
                    "anti_captcha_enabled": True,
                    "human_actions": 0,
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

        finally:
            if profile_uuid:
                self._stop_profile(profile_uuid)
