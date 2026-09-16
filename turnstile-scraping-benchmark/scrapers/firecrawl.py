from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from firecrawl import Firecrawl

from .base import ScrapeResult

load_dotenv()


class FirecrawlScraper:
    """Firecrawl enhanced-proxy configuration with interactive login."""

    name = "firecrawl_stealth"

    def __init__(self, timeout_seconds: int = 60):
        api_key = os.getenv("FIRECRAWL_API_KEY")

        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is not set")

        self.client = Firecrawl(api_key=api_key)

        self.timeout_seconds = timeout_seconds

    def scrape(
        self,
        target: dict[str, Any],
    ) -> ScrapeResult:
        started = time.perf_counter()
        scrape_id = None

        try:
            result = self.client.scrape(
                target["url"],
                formats=["html"],
                proxy="enhanced",
                store_in_cache=False,
                timeout=self.timeout_seconds * 1000,
            )

            metadata = getattr(
                result,
                "metadata",
                None,
            )

            metadata_dict: dict[str, Any] = {}

            if metadata is not None:
                if hasattr(
                    metadata,
                    "model_dump",
                ):
                    metadata_dict = metadata.model_dump()

                elif isinstance(
                    metadata,
                    dict,
                ):
                    metadata_dict = metadata

                else:
                    metadata_dict = {
                        k: v for k, v in vars(metadata).items() if not k.startswith("_")
                    }

            scrape_id = getattr(
                metadata,
                "scrape_id",
                None,
            ) or metadata_dict.get("scrapeId")

            if not scrape_id:
                raise RuntimeError("Firecrawl did not return a scrape_id")

            interaction = target.get("interaction")

            if interaction and interaction.get("type") == "turnstile_login":
                email_selector = interaction["email_selector"]

                password_selector = interaction["password_selector"]

                submit_selector = interaction["submit_selector"]

                success_selector = interaction["success_selector"]

                success_url_contains = interaction["success_url_contains"]

                email = interaction["email"]

                password = interaction["password"]

                login_code = f"""
await page.waitForSelector(
    {json.dumps(email_selector)},
    {{ state: "visible", timeout: 30000 }}
);

await page.fill(
    {json.dumps(email_selector)},
    {json.dumps(email)}
);

await page.fill(
    {json.dumps(password_selector)},
    {json.dumps(password)}
);

await page.click(
    {json.dumps(submit_selector)}
);

await page.waitForURL(
    "**{success_url_contains}**",
    {{ timeout: 30000 }}
);

await page.waitForSelector(
    {json.dumps(success_selector)},
    {{ state: "visible", timeout: 30000 }}
);

const html = await page.content();
const title = await page.title();
const url = await page.url();

JSON.stringify({{
    html,
    title,
    url
}});
"""

                interaction_result = self.client.interact(
                    scrape_id,
                    code=login_code,
                    language="node",
                    timeout=self.timeout_seconds,
                )

                if not getattr(
                    interaction_result,
                    "success",
                    False,
                ):
                    stderr = getattr(
                        interaction_result,
                        "stderr",
                        "",
                    )

                    error = getattr(
                        interaction_result,
                        "error",
                        "",
                    )

                    details = stderr or error or "unknown Firecrawl interaction error"

                    raise RuntimeError(
                        "Firecrawl login interaction failed: " f"{details}"
                    )

                raw_result = getattr(
                    interaction_result,
                    "result",
                    None,
                )

                if not raw_result:
                    raise RuntimeError(
                        "Firecrawl interaction completed " "but returned no result"
                    )

                try:
                    page_data = json.loads(raw_result)

                except (
                    TypeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise RuntimeError(
                        "Could not parse Firecrawl " "interaction result"
                    ) from exc

                html = page_data.get("html") or ""

                title = page_data.get("title")

                final_url = page_data.get("url")

                if not html:
                    raise RuntimeError(
                        "Firecrawl returned an empty " "authenticated page"
                    )

                if not final_url or success_url_contains not in final_url:
                    raise RuntimeError(
                        "Firecrawl interaction did not "
                        "end on the expected authenticated URL: "
                        f"{final_url}"
                    )

            else:
                html = (
                    getattr(
                        result,
                        "html",
                        None,
                    )
                    or ""
                )

                title = metadata_dict.get("title")

            elapsed_ms = (time.perf_counter() - started) * 1000

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
                title=title,
                metadata={
                    **metadata_dict,
                    "stealth_config": ("enhanced_proxy"),
                    "interactive_login": bool(
                        interaction and interaction.get("type") == "turnstile_login"
                    ),
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
                    "stealth_config": ("enhanced_proxy"),
                    "interactive_login": bool(
                        target.get("interaction")
                        and target["interaction"].get("type") == "turnstile_login"
                    ),
                },
            )

        finally:
            if scrape_id:
                try:
                    self.client.stop_interaction(scrape_id)
                except Exception:
                    pass
