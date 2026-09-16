# Web Scraping Benchmarks

A reproducible benchmark for evaluating web scraping approaches across unprotected, bot-protected, and authenticated web environments.

The repository compares four approaches:

- Firecrawl
- Browserless
- SeleniumBase
- Surfsky

The benchmark is organized into three separate categories:

- **Standard Scraping Benchmark** — evaluates the approaches using their standard configurations.
- **Stealth Scraping Benchmark** — evaluates the approaches using their stealth-oriented configurations.
- **Turnstile Login Benchmark** — evaluates the approaches against an interactive login workflow protected by Cloudflare Turnstile.

The three categories are analyzed separately rather than combined into a single score.

## Benchmark Categories

### Standard Scraping Benchmark

The Standard benchmark evaluates Firecrawl, Browserless, SeleniumBase, and Surfsky using their standard benchmark configurations.

It includes the unprotected ScrapingCourse Ecommerce page as a baseline, together with bot-protected target environments representing Cloudflare, DataDome, and Akamai.

See [`standard/README.md`](standard-scraping-benchmark/README.md) for the methodology, configurations, extraction tasks, validation criteria, and run instructions.

### Stealth Scraping Benchmark

The Stealth benchmark evaluates the same approaches using their stealth-oriented configurations.

The purpose is to measure how these configurations perform against the selected protected target environments in terms of scraping success, execution time, and reliability.

The Stealth benchmark is treated as a separate configuration experiment. Its results are not combined with or used to replace the Standard benchmark results.

See [`stealth/README.md`](stealth-scraping-benchmark/README.md) for the methodology, configurations, extraction tasks, validation criteria, and run instructions.

### Turnstile Login Benchmark

The Turnstile benchmark evaluates the approaches against an interactive login workflow protected by Cloudflare Turnstile.

Unlike the Standard and Stealth benchmarks, this test requires each approach to complete the login workflow, reach the authenticated dashboard, and then extract and validate the expected data.

The Turnstile benchmark is treated as a separate workflow experiment because its execution requirements differ from the page retrieval tests used in the other categories.

See [`turnstile-scraping-benchmark/README.md`](turnstile/README.md) for the methodology, configurations, extraction workflow, validation criteria, and run instructions.

## Approaches

All benchmark categories evaluate:

- **Firecrawl** — managed scraping API
- **Browserless** — managed browser and scraping infrastructure
- **SeleniumBase** — local browser automation
- **Surfsky** — managed browser infrastructure

Each benchmark category defines the specific configuration and execution workflow used for each approach.

## Methodology

The benchmark categories follow the same core principles:

1. Freeze the extraction tasks and validation rules before definitive runs.
2. Validate each adapter with a small smoke test before running the benchmark.
3. Apply the same number of iterations consistently across approach × target combinations.
4. Measure end-to-end scraping reliability rather than provider-level success responses alone.
5. Preserve raw experimental evidence so individual results can be audited.
6. Analyze the Standard, Stealth, and Turnstile configurations separately.

A run is considered successful only when the expected target data is retrieved and passes the benchmark's extraction validator.

An HTTP 200 response, provider-level success response, or challenge/solver signal alone does not constitute a successful scrape.

## Timing

Elapsed time starts immediately before the approach execution and ends when usable target HTML is returned.

Approach-specific setup is included in the measured interval, such as browser startup or remote profile creation.

Post-response cleanup is excluded from the timed interval where applicable.

## Repository Structure

```text
scraping-benchmarks/

├── .env.example
├── .gitignore
├── requirements.txt
│
├── standard-scraping-benchmark/
│   ├── README.md
│   ├── benchmark/
│   ├── config/
│   ├── scrapers/
│   └── results/
│
├── stealth-scraping-benchmark/
│   ├── README.md
│   ├── benchmark/
│   ├── config/
│   ├── scrapers/
│   └── results/
│
└── turnstile-scraping-benchmark/
    ├── README.md
    ├── benchmark/
    ├── config/
    ├── scrapers/
    └── results/

### Shared files

- `.env.example` — environment variable template
- `requirements.txt` — shared Python dependencies
- `.gitignore` — repository-wide ignore rules

### Benchmark directories

Each benchmark category contains its own configuration, scraper adapters, benchmark runner, validation logic, evidence collection, and generated results.

## Setup

From the repository root, install the shared dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template:

```bash
copy .env.example .env
```

Add the required API credentials to `.env`.

## Running a Benchmark

Each category has its own README with the specific run instructions.

For the Standard benchmark:

```bash
cd standard-scraping-benchmark
python -m benchmark.runner
```

For the Stealth benchmark:

```bash
cd scraping-benchmark-stealth
python -m benchmark.runner
```

## Reproducibility and Evidence

The benchmark keeps the experiment configuration, extraction rules, validators, scraper adapters, runner, and evidence collection code in the repository.

Generated benchmark results are kept in each category's `results/` directory.

Raw experimental records include returned HTML together with metadata, timing information, and validation results so that benchmark outcomes can be audited after a run.

Before running a definitive benchmark, ensure that the target configuration, extraction selectors, validation rules, and benchmark configuration are frozen.
