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
    SeleniumBaseScraper,
    SurfskyScraper,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

SCRAPER_CLASSES = {
    "firecrawl": FirecrawlScraper,
    "browserless": BrowserlessScraper,
    "seleniumbase": SeleniumBaseScraper,
    "surfsky": SurfskyScraper,
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    # Load environment variables from the project-level .env file.
    load_dotenv(ROOT / ".env")

    benchmark_config = load_yaml(CONFIG_DIR / "benchmark.yaml")["benchmark"]

    targets = load_yaml(CONFIG_DIR / "targets.yaml")["targets"]

    iterations = benchmark_config["iterations"]
    timeout_seconds = benchmark_config["timeout_seconds"]
    approaches = benchmark_config["approaches"]

    # Allow each benchmark/revalidation run to use its own
    # results directory. Defaults to "results" so the normal
    # benchmark behavior remains unchanged.
    results_dir_config = benchmark_config.get(
        "output_dir",
        "results",
    )

    RESULTS_DIR = ROOT / results_dir_config
    RAW_DIR = RESULTS_DIR / "raw"

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_path = RESULTS_DIR / "summary.csv"

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
        "provider_status_code",
        "target_status_code",
        "error",
    ]

    # Instantiate each scraper once and reuse it across runs.
    scraper_instances = {}

    for approach in approaches:
        scraper_class = SCRAPER_CLASSES.get(approach)

        if scraper_class is None:
            raise ValueError(f"Unknown approach configured: {approach}")

        scraper_instances[approach] = scraper_class(timeout_seconds)

    with summary_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for target in targets:
            for approach in approaches:
                scraper = scraper_instances[approach]

                for run_number in range(
                    1,
                    iterations + 1,
                ):
                    print(
                        f"[{approach}] "
                        f"{target['id']} "
                        f"run {run_number}/{iterations}"
                    )

                    result = scraper.scrape(target)

                    validation = validate(
                        target,
                        result.html,
                    )

                    # A provider/API response does not constitute a
                    # successful benchmark result. The benchmark passes
                    # only when the expected content is extracted and
                    # validated.
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
                        "records_expected": (validation.records_expected),
                        "elapsed_ms": round(
                            result.elapsed_ms,
                            2,
                        ),
                        "provider_status_code": (result.provider_status_code),
                        "target_status_code": (result.target_status_code),
                        "error": result.error,
                    }

                    writer.writerow(record)
                    csv_file.flush()

                    raw_payload = {
                        **result.to_dict(),
                        "run": run_number,
                        "validation": validation.to_dict(),
                    }

                    if benchmark_config.get(
                        "save_raw_output",
                        True,
                    ):
                        save_raw_result(
                            RAW_DIR,
                            raw_payload,
                            html=result.html,
                        )

                    # Keep the console output useful during the
                    # smoke test.
                    print(
                        f"    result="
                        f"{'PASS' if final_success else 'FAIL'} "
                        f"| records="
                        f"{validation.records_found}/"
                        f"{validation.records_expected} "
                        f"| elapsed="
                        f"{result.elapsed_ms:.0f} ms "
                        f"| provider="
                        f"{result.provider_status_code} "
                        f"| target="
                        f"{result.target_status_code}"
                    )

                    if validation.reason:
                        print(f"    reason=" f"{validation.reason}")

                    if result.error:
                        print(f"    error=" f"{result.error}")

    print()
    print(f"Benchmark complete. " f"Summary written to: {summary_path}")


if __name__ == "__main__":
    main()
