from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScrapeResult:
    approach: str
    target_id: str
    url: str
    success: bool
    elapsed_ms: float
    html: str = ""
    status_code: int | None = None
    title: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approach": self.approach,
            "target_id": self.target_id,
            "url": self.url,
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "status_code": self.status_code,
            "title": self.title,
            "error": self.error,
            "metadata": self.metadata,
        }
