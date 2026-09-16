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
        successes = [
            row for row in items
            if row["success"].lower() == "true"
        ]

        times = [
            float(row["elapsed_ms"])
            for row in items
            if row["elapsed_ms"]
        ]

        summary.append({
            "target_id": target_id,
            "approach": approach,
            "runs": len(items),
            "successful_runs": len(successes),
            "success_rate_pct": (
                len(successes) / len(items) * 100
                if items else 0
            ),
            "median_elapsed_ms": (
                statistics.median(times) if times else None
            ),
            "mean_elapsed_ms": (
                statistics.mean(times) if times else None
            ),
        })

    return summary
