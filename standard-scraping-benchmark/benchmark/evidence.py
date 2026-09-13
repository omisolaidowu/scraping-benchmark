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

    base_name = (
        f"{result['target_id']}_" f"{result['approach']}_" f"run_{result['run']:02d}"
    )

    json_path = output_dir / f"{base_name}.json"

    payload = dict(result)

    # Keep the raw result JSON focused on metadata and validation.
    # HTML is stored separately so large documents do not inflate
    # every JSON evidence file.
    payload.pop("html", None)

    if html is not None:
        html_dir = output_dir.parent / "evidence"
        html_dir.mkdir(parents=True, exist_ok=True)

        html_path = html_dir / f"{base_name}.html"

        html_path.write_text(
            html,
            encoding="utf-8",
        )

        payload["html_path"] = str(html_path.relative_to(output_dir.parent))

    json_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return json_path
