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
        interaction = target.get("interaction")
        extraction = target["extraction"]

        url = target["url"]
        record_selector = extraction["record_selector"]

        if interaction and interaction.get("type") == "turnstile_login":
            waf_selector = interaction["waf_selector"]
            email_selector = interaction["email_selector"]
            password_selector = interaction["password_selector"]
            submit_selector = interaction["submit_selector"]
            success_selector = interaction["success_selector"]
            success_url_contains = interaction["success_url_contains"]

            email = interaction["email"]
            password = interaction["password"]

            return f"""
mutation TurnstileLogin {{
  goto(
    url: {self._graphql_string(url)}
    waitUntil: networkIdle
  ) {{
    status
    time
  }}

  waf: waitForSelector(
    selector: {self._graphql_string(waf_selector)}
    timeout: 30000
  ) {{
    time
  }}

  solve(
    type: cloudflare
    timeout: 60000
  ) {{
    found
    solved
    time
  }}

  email: type(
    selector: {self._graphql_string(email_selector)}
    text: {self._graphql_string(email)}
  ) {{
    selector
    time
  }}

  password: type(
    selector: {self._graphql_string(password_selector)}
    text: {self._graphql_string(password)}
  ) {{
    selector
    time
  }}

  submit: click(
    selector: {self._graphql_string(submit_selector)}
    visible: true
    timeout: 30000
  ) {{
    time
  }}



  authenticated: waitForSelector(
    selector: {self._graphql_string(success_selector)}
    timeout: 30000
  ) {{
    time
  }}

  finalUrl: url {{
    url
  }}

  pageHtml: html {{
    html
  }}
}}
"""

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

            interaction = target.get("interaction")

            if interaction and interaction.get("type") == "turnstile_login":
                solve_data = data.get("solve") or {}

                found = solve_data.get("found")

                solved = solve_data.get("solved")

                final_url_data = data.get("finalUrl") or {}

                final_url = final_url_data.get("url") or ""

                expected_url = interaction["success_url_contains"]

                if not found:
                    raise RuntimeError(
                        "Browserless did not detect "
                        "a Cloudflare challenge. "
                        f"Final URL: {final_url}"
                    )

                if not solved:
                    raise RuntimeError(
                        "Browserless detected the "
                        "Cloudflare challenge but "
                        "did not solve it. "
                        f"Final URL: {final_url}"
                    )

                if expected_url not in final_url:
                    raise RuntimeError(
                        "Browserless solved the Cloudflare "
                        "challenge but did not reach the "
                        "expected authenticated URL. "
                        f"Expected: {expected_url}; "
                        f"Actual: {final_url}"
                    )

                page_html_data = data.get("pageHtml") or {}

                html = page_html_data.get("html") or ""

                if not html:
                    raise RuntimeError(
                        "Browserless reached the authenticated "
                        "URL but returned no page HTML"
                    )

            else:
                page_html_data = data.get("pageHtml") or {}

                html = page_html_data.get("html") or ""

                final_url = ""

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
                    "solve_captchas": bool(
                        interaction and interaction.get("type") == "turnstile_login"
                    ),
                    "captcha_type": (
                        "cloudflare"
                        if (
                            interaction and interaction.get("type") == "turnstile_login"
                        )
                        else None
                    ),
                    "turnstile_login": bool(
                        interaction and interaction.get("type") == "turnstile_login"
                    ),
                    "turnstile_found": (
                        solve_data.get("found")
                        if (
                            interaction and interaction.get("type") == "turnstile_login"
                        )
                        else None
                    ),
                    "turnstile_solved": (
                        solve_data.get("solved")
                        if (
                            interaction and interaction.get("type") == "turnstile_login"
                        )
                        else None
                    ),
                    "final_url": final_url,
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
                error=(f"{type(exc).__name__}: {exc}"),
                metadata={
                    "endpoint": "/stealth/bql",
                    "stealth": True,
                    "proxy": "residential",
                    "humanlike": True,
                    "proxy_locale_match": True,
                    "solve_captchas": bool(
                        target.get("interaction")
                        and target["interaction"].get("type") == "turnstile_login"
                    ),
                    "captcha_type": (
                        "cloudflare"
                        if (
                            target.get("interaction")
                            and target["interaction"].get("type") == "turnstile_login"
                        )
                        else None
                    ),
                    "turnstile_login": bool(
                        target.get("interaction")
                        and target["interaction"].get("type") == "turnstile_login"
                    ),
                },
            )
