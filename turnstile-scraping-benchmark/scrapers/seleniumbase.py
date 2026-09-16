from __future__ import annotations

import time
from typing import Any

from seleniumbase import SB

from .base import ScrapeResult


class SeleniumBaseScraper:
    name = "seleniumbase"

    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def scrape(self, target: dict[str, Any]) -> ScrapeResult:
        started = time.perf_counter()

        interaction = target.get("interaction") or {}
        interaction_type = interaction.get("type")

        try:
            with SB(
                uc=True,
                headless=True,
            ) as sb:

                sb.uc_open_with_reconnect(
                    target["url"],
                    reconnect_time=4,
                )

                if interaction_type == "turnstile_login":
                    self._run_turnstile_login(
                        sb,
                        interaction,
                    )

                html = sb.get_page_source() or ""
                title = sb.get_title()

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
                        "uc_mode": True,
                        "headless": True,
                        "interaction_type": interaction_type,
                        "turnstile_login": (interaction_type == "turnstile_login"),
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
                error=(f"{type(exc).__name__}: {exc}"),
                metadata={
                    "uc_mode": True,
                    "headless": True,
                    "interaction_type": interaction_type,
                },
            )

    def _run_turnstile_login(
        self,
        sb: Any,
        interaction: dict[str, Any],
    ) -> None:
        email_selector = interaction.get(
            "email_selector",
            "#email",
        )

        password_selector = interaction.get(
            "password_selector",
            "#password",
        )

        submit_selector = interaction.get(
            "submit_selector",
            "#submit-button",
        )

        response_selector = interaction.get(
            "response_selector",
            'input[name="cf-turnstile-response"]',
        )

        success_selector = interaction.get(
            "success_selector",
            "div.product-item",
        )

        success_url_contains = interaction.get(
            "success_url_contains",
            "/dashboard",
        )

        email = interaction["email"]
        password = interaction["password"]

        print("  → Filling Turnstile test credentials")

        sb.type(
            email_selector,
            email,
        )

        sb.type(
            password_selector,
            password,
        )

        print("  → Waiting for Turnstile response...")

        response_populated = False
        deadline = time.time() + 15

        while time.time() < deadline:
            try:
                response_value = sb.get_attribute(
                    response_selector,
                    "value",
                )

                if response_value:
                    response_populated = True
                    break

            except Exception:
                pass

            sb.sleep(0.5)

        print("  → Turnstile response populated: " f"{response_populated}")

        if not response_populated:
            raise RuntimeError(
                "Turnstile response was not populated " "in headless mode"
            )

        print("  → Submitting Turnstile-protected form")

        sb.uc_click(
            submit_selector,
            reconnect_time=2,
        )

        try:
            sb.wait_for_element_present(
                success_selector,
                timeout=15,
            )
        except Exception:
            pass

        current_url = sb.get_current_url()
        title = sb.get_title()

        print(f"  → Post-submit URL: {current_url}")

        print(f"  → Post-submit title: {title}")

        try:
            product_count = len(sb.find_elements(success_selector))
        except Exception:
            product_count = 0

        print("  → Post-submit product cards: " f"{product_count}")

        if success_url_contains:
            if success_url_contains not in current_url:
                print(
                    "  → Warning: expected "
                    "authenticated URL fragment "
                    f"'{success_url_contains}' "
                    "not found"
                )
