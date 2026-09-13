from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScrapeResult:
    approach: str
    target_id: str
    url: str

    # Whether the scraping provider/API request itself succeeded.
    success: bool

    # End-to-end time for the approach to return a response.
    elapsed_ms: float

    # Returned page content.
    html: str = ""

    # HTTP status returned by the scraping provider/API.
    provider_status_code: int | None = None

    # HTTP status returned by the target website, when available.
    target_status_code: int | None = None

    title: str | None = None
    error: str | None = None

    # Provider-specific information that doesn't belong
    # in the common fields above.
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approach": self.approach,
            "target_id": self.target_id,
            "url": self.url,
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "provider_status_code": self.provider_status_code,
            "target_status_code": self.target_status_code,
            "title": self.title,
            "error": self.error,
            "metadata": self.metadata,
        }
