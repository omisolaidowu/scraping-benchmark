from __future__ import annotations

import os
import time
from typing import Any

import requests
from patchright.sync_api import sync_playwright

from .base import ScrapeResult
from dotenv import load_dotenv

load_dotenv()


class SurfskyScraper:
    """Surfsky cloud browser via Patchright/CDP with explicit Turnstile solving."""

    name = "surfsky"

    def __init__(self, timeout_seconds: int = 60):
        token = os.getenv("SURFSKY_API_TOKEN")
        if not token:
            raise RuntimeError("SURFSKY_API_TOKEN is not set")

        self.token = token
        self.timeout_seconds = timeout_seconds
        self.base_url = os.getenv(
            "SURFSKY_API_BASE_URL",
            "https://api-public.surfsky.io",
        ).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Cloud-Api-Token": self.token,
        }

    def _create_profile(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "anti_captcha": {
                "enabled": True,
                "auto_captcha_types": [
                    "turnstile",
                    "recaptcha",
                    "datadome",
                ],
            },
            "browser_settings": {
                "inactive_kill_timeout": max(
                    60,
                    self.timeout_seconds + 10,
                ),
            },
        }

        # Surfsky uses its account/default proxy pool unless
        # SURFSKY_PROXY is explicitly supplied.
        proxy = os.getenv("SURFSKY_PROXY")
        if proxy:
            data["proxy"] = proxy

        response = requests.post(
            f"{self.base_url}/profiles/one_time",
            headers=self._headers(),
            json=data,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        return response.json()

    def _stop_profile(self, profile_uuid: str | None) -> None:
        if not profile_uuid:
            return

        try:
            requests.post(
                f"{self.base_url}/profiles/{profile_uuid}/stop",
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except Exception:
            # Cleanup failure should not replace the actual benchmark result.
            pass

    def _turnstile_script_detected(self, page) -> bool:
        """
        Detect whether the page loads Cloudflare Turnstile-related code.

        This is informational only. It is NOT enough by itself to call
        Captcha.solve because Cloudflare can load the Turnstile script
        without an active CAPTCHA widget being present.
        """
        try:
            html = page.content().lower()
        except Exception:
            return False

        markers = [
            "challenges.cloudflare.com/turnstile",
            "cf-turnstile",
            "turnstile.render",
            "turnstile.execute",
        ]

        return any(marker in html for marker in markers)

    def _turnstile_widget_detected(self, page) -> bool:
        """
        Detect an actual Turnstile widget that Surfsky's CDP solver
        can potentially attach to.

        Do NOT treat the presence of the Turnstile JavaScript alone
        as proof that a CAPTCHA is active.
        """
        selectors = [
            'iframe[src*="challenges.cloudflare.com"]',
            'iframe[src*="turnstile"]',
            'iframe[title*="Turnstile"]',
            ".cf-turnstile",
            '[class*="cf-turnstile"]',
            "[data-sitekey]",
        ]

        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    return True
            except Exception:
                pass

        return False

    def _wait_for_turnstile(self, page, timeout_seconds: int = 10) -> bool:
        """
        Give Cloudflare a short window to render the widget.

        We check repeatedly rather than assuming that the widget is
        already present immediately after domcontentloaded.
        """
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            if self._turnstile_widget_detected(page):
                return True

            time.sleep(0.5)

        return False

    def _solve_turnstile(self, cdp) -> dict[str, Any]:
        print("      → Calling Surfsky Turnstile solver...")

        result = cdp.send(
            "Captcha.solve",
            {
                "type": "turnstile",
                "timeout": 60_000,
            },
        )

        print(f"      → Turnstile solver response: {result}")

        return result

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        profile_uuid: str | None = None
        html: str | None = None
        title: str | None = None

        turnstile_script_detected = False
        turnstile_widget_detected = False
        turnstile_solver_used = False
        turnstile_solver_result: dict[str, Any] | None = None

        try:
            profile = self._create_profile()

            profile_uuid = profile["internal_uuid"]
            ws_url = profile["ws_url"]

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(ws_url)

                context = browser.contexts[0]

                page = context.pages[0] if context.pages else context.new_page()

                print(f"      → Navigating to {target['url']}")

                page.goto(
                    target["url"],
                    wait_until="domcontentloaded",
                    timeout=self.timeout_seconds * 1000,
                )

                # First determine whether Cloudflare Turnstile code is
                # present at all.
                turnstile_script_detected = self._turnstile_script_detected(page)

                print(
                    "      → Turnstile script detected: " f"{turnstile_script_detected}"
                )

                # Now wait briefly for an actual widget to appear.
                turnstile_widget_detected = self._wait_for_turnstile(
                    page,
                    timeout_seconds=10,
                )

                print(
                    "      → Turnstile widget detected: " f"{turnstile_widget_detected}"
                )

                # Only invoke Captcha.solve when there is evidence of an
                # actual Turnstile widget. This avoids the previous
                # "No captcha detected on the page" error caused by
                # detecting only the Turnstile script.
                if turnstile_widget_detected:
                    cdp = browser.new_browser_cdp_session()

                    turnstile_solver_used = True

                    turnstile_solver_result = self._solve_turnstile(cdp)

                    # Give the page a moment to process the solved challenge.
                    time.sleep(3)

                # Capture the final state after solving, if applicable.
                html = page.content()
                title = page.title()

                # Connected-over-CDP browser.close() disconnects the client.
                # Use the CDP Browser.close command to stop the remote
                # Surfsky browser cleanly.
                try:
                    cdp = browser.new_browser_cdp_session()
                    cdp.send("Browser.close")
                except Exception:
                    pass

            elapsed_ms = (time.perf_counter() - started) * 1000

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=bool(html),
                elapsed_ms=elapsed_ms,
                html=html,
                status_code=None,
                title=title,
                metadata={
                    "browser": "surfsky_cdp",
                    "playwright_variant": "patchright",
                    "anti_captcha": True,
                    "auto_captcha_types": [
                        "turnstile",
                        "recaptcha",
                        "datadome",
                    ],
                    "explicit_proxy": bool(os.getenv("SURFSKY_PROXY")),
                    "profile_uuid": profile_uuid,
                    "turnstile_script_detected": turnstile_script_detected,
                    "turnstile_widget_detected": turnstile_widget_detected,
                    "turnstile_solver_used": turnstile_solver_used,
                    "turnstile_solver_result": turnstile_solver_result,
                },
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000

            # Preserve whatever page state we managed to capture before
            # the exception.
            self._stop_profile(profile_uuid)

            return ScrapeResult(
                approach=self.name,
                target_id=target["id"],
                url=target["url"],
                success=False,
                elapsed_ms=elapsed_ms,
                html=html,
                status_code=None,
                title=title,
                error=f"{type(exc).__name__}: {exc}",
                metadata={
                    "browser": "surfsky_cdp",
                    "playwright_variant": "patchright",
                    "anti_captcha": True,
                    "auto_captcha_types": [
                        "turnstile",
                        "recaptcha",
                        "datadome",
                    ],
                    "explicit_proxy": bool(os.getenv("SURFSKY_PROXY")),
                    "profile_uuid": profile_uuid,
                    "turnstile_script_detected": turnstile_script_detected,
                    "turnstile_widget_detected": turnstile_widget_detected,
                    "turnstile_solver_used": turnstile_solver_used,
                    "turnstile_solver_result": turnstile_solver_result,
                },
            )

        finally:
            # The normal successful path already closes the browser via
            # CDP. This is a fallback for errors that happen earlier.
            self._stop_profile(profile_uuid)
