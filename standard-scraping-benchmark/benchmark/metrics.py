from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path


def load_summary(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def calculate(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)

    for row in rows:
        key = (row["target_id"], row["approach"])
        groups[key].append(row)

    summary = []

    for (target_id, approach), items in groups.items():
        successful_runs = [
            row for row in items if row["validation_passed"].lower() == "true"
        ]

        provider_successes = [
            row
            for row in items
            if row["provider_status_code"]
            and 200 <= int(row["provider_status_code"]) < 300
        ]

        times = [float(row["elapsed_ms"]) for row in items if row["elapsed_ms"]]

        target_statuses = [
            int(row["target_status_code"]) for row in items if row["target_status_code"]
        ]

        summary.append(
            {
                "target_id": target_id,
                "approach": approach,
                "runs": len(items),
                # Actual benchmark outcome.
                "successful_runs": len(successful_runs),
                "success_rate_pct": (
                    len(successful_runs) / len(items) * 100 if items else 0
                ),
                # Provider/API health.
                "provider_successes": len(provider_successes),
                "provider_success_rate_pct": (
                    len(provider_successes) / len(items) * 100 if items else 0
                ),
                # Latency.
                "median_elapsed_ms": (statistics.median(times) if times else None),
                "mean_elapsed_ms": (statistics.mean(times) if times else None),
                # Target HTTP status information.
                "target_status_codes": (
                    sorted(set(target_statuses)) if target_statuses else []
                ),
            }
        )

    return summary
