from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_raw_result(
    output_dir: str | Path,
    result: dict[str, Any],
    html: str | None = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{result['target_id']}_"
        f"{result['approach']}_"
        f"run_{result['run']:02d}.json"
    )

    path = output_dir / filename

    payload = dict(result)
    if html is not None:
        payload["html"] = html

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return path
