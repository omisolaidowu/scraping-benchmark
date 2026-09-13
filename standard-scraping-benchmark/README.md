# Web Scraping Benchmark

A benchmark comparing Firecrawl, Browserless, SeleniumBase, and Surfsky across
the same extraction tasks under different protection conditions.

The benchmark includes an unprotected baseline as a control and separate
bot-protected target environments representing common protection systems.

## Approaches

### Firecrawl

Uses the Firecrawl Scrape API with its standard configuration.

### Browserless

Uses Browserless as a managed browser and scraping service using its standard
configuration.

### SeleniumBase

Uses SeleniumBase with UC Mode:

- `uc=True`
- `headless=True`

UC Mode is treated as SeleniumBase's expected anti-detection configuration.
No additional stealth configuration is introduced in the Standard benchmark.

### Surfsky

Uses Surfsky's managed browser infrastructure over CDP using its standard
browser configuration.

## Methodology

The benchmark evaluates each approach against the same extraction tasks and
validation rules.

The primary benchmark includes both an unprotected baseline and
bot-protected targets. The unprotected baseline is treated as a control and
is analyzed separately from the protected-target results.

Each approach × target combination is run using the same configured number of
iterations.

A 2-run smoke test is performed first to verify that the extraction logic,
selectors, validation, and adapter configuration are working correctly.
Definitive benchmark runs are performed only after the configuration is
frozen.

The benchmark is designed to measure end-to-end scraping reliability rather
than simply whether a provider returns an HTTP success response.

## Success Criteria

A run is considered successful only when the expected target data is retrieved
and passes the benchmark's extraction validator.

An HTTP 200 response, provider-level success response, or challenge/solver
signal alone does not constitute a successful scrape.

An unconfigured target must never count as a benchmark pass.

## Extraction & Validation

Each target has a defined extraction task in `config/targets.yaml`.

The validator checks whether the returned content contains the expected
records and fields for that target.

Raw responses and validation metadata are retained as experimental evidence so
that individual benchmark outcomes can be audited.

## Timing

Elapsed time starts immediately before the approach execution and ends when
usable target HTML is returned.

Approach-specific setup is included in the timed interval, such as browser
startup or remote profile creation.

Post-response cleanup is excluded from the timed interval where applicable.

## Architecture

- `config/` — experiment configuration
- `scrapers/` — one adapter per approach
- `benchmark/runner.py` — orchestrates benchmark runs
- `benchmark/validator.py` — validates extracted data
- `benchmark/evidence.py` — stores raw experimental evidence
- `benchmark/metrics.py` — calculates aggregate metrics
- `results/` — generated benchmark output

## Setup

From the repository root, install the shared benchmark dependencies:

```bash
pip install -r requirements.txt