from __future__ import annotations

import csv
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from benchmark.evidence import save_raw_result
from benchmark.validator import validate
from scrapers import (
    BrowserlessScraper,
    FirecrawlScraper,
    SurfskyScraper,
    SeleniumBaseScraper,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

SCRAPER_CLASSES = {
    "firecrawl": FirecrawlScraper,
    "browserless": BrowserlessScraper,
    "surfsky": SurfskyScraper,
    "seleniumbase": SeleniumBaseScraper,
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    load_dotenv(ROOT / ".env")

    benchmark_config = load_yaml(CONFIG_DIR / "benchmark.yaml")["benchmark"]
    targets = load_yaml(CONFIG_DIR / "targets.yaml")["targets"]

    iterations = benchmark_config["iterations"]
    timeout_seconds = benchmark_config["timeout_seconds"]
    approaches = benchmark_config["approaches"]

    results_dir = ROOT / benchmark_config.get("output_dir", "results")
    raw_dir = results_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    summary_path = results_dir / "summary.csv"

    fieldnames = [
        "timestamp",
        "target_id",
        "target_name",
        "protection",
        "approach",
        "run",
        "success",
        "validation_passed",
        "validation_reason",
        "records_found",
        "records_expected",
        "elapsed_ms",
        "status_code",
        "error",
    ]

    scraper_instances = {
        name: SCRAPER_CLASSES[name](timeout_seconds) for name in approaches
    }

    with summary_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for target in targets:
            for approach in approaches:
                scraper = scraper_instances[approach]

                for run_number in range(1, iterations + 1):
                    print(
                        f"[{approach}] {target['id']} " f"run {run_number}/{iterations}"
                    )

                    result = scraper.scrape(target)
                    validation = validate(target, result.html)
                    final_success = validation.passed

                    record = {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "target_id": target["id"],
                        "target_name": target["name"],
                        "protection": target["protection"],
                        "approach": approach,
                        "run": run_number,
                        "success": final_success,
                        "validation_passed": validation.passed,
                        "validation_reason": validation.reason,
                        "records_found": validation.records_found,
                        "records_expected": validation.records_expected,
                        "elapsed_ms": round(result.elapsed_ms, 2),
                        "status_code": result.status_code,
                        "error": result.error,
                    }

                    writer.writerow(record)
                    csv_file.flush()

                    raw_payload = {
                        **result.to_dict(),
                        "run": run_number,
                        "validation": validation.to_dict(),
                    }

                    if benchmark_config.get("save_raw_output", True):
                        save_raw_result(raw_dir, raw_payload, html=result.html)

                    print(
                        f"    result={'PASS' if final_success else 'FAIL'} "
                        f"| records={validation.records_found}/"
                        f"{validation.records_expected} "
                        f"| elapsed={result.elapsed_ms:.0f} ms"
                    )
                    if validation.reason:
                        print(f"    reason={validation.reason}")
                    if result.error:
                        print(f"    error={result.error}")

    print(f"Benchmark complete. Summary written to: {summary_path}")


if __name__ == "__main__":
    main()
