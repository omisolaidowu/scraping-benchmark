# Stealth Scraping Benchmark

A companion benchmark to the primary scraping benchmark. It uses the same target environments, extraction rules, validation logic, timeout, latency measurement, and raw evidence capture, but evaluates the approaches using their stealth-oriented configurations.

This benchmark should be treated as a separate configuration experiment. Results are not combined with or used to replace the primary benchmark results.

## Approaches

### Firecrawl

Uses the Firecrawl Scrape API with `proxy="enhanced"`.

Firecrawl's enhanced proxy is used as its API-level configuration for sites requiring greater resistance to anti-bot measures. This is a proxy configuration rather than a browser-level stealth mode.

### Browserless

Uses the Browserless BrowserQL `/stealth/bql` endpoint with:

- `proxy="residential"`
- `humanlike=true`
- `proxyLocaleMatch=1`

The browser navigates to the target, waits for the expected content selector, and returns the full page HTML for extraction and validation.

### Surfsky

Uses Surfsky's cloud browser over CDP with Patchright, following Surfsky's recommended approach for browser automation against bot-protected sites.

The same extraction and validation process is applied to the returned page content.

### SeleniumBase

Uses SeleniumBase UC Mode with `uc=True` and headless Chromium.

UC Mode is treated as SeleniumBase's stealth-oriented browser configuration for this benchmark. No additional stealth configuration is introduced for SeleniumBase in this category.

## Methodology

The benchmark is deliberately comparable to the primary benchmark but should be treated as a separate configuration experiment.

The main question is how the stealth-oriented configurations perform against the selected protected targets in terms of successful extraction, execution time, and reliability across repeated runs.

Run a 2-run smoke test first. If the configuration and extraction are sound, run the definitive benchmark using the configured number of iterations.

The same number of runs is applied consistently across all approach × target combinations.

Do not replace the primary benchmark results with these results. Analyze the two configurations separately.

## Success Criteria

A run is considered successful only when the expected target data is successfully retrieved and passes the benchmark's extraction validator.

HTTP status codes, provider success responses, or CAPTCHA/Turnstile solver signals alone do not constitute a successful scrape.

## Timing

Elapsed time starts immediately before the approach execution and ends when usable target HTML is returned.

Approach-specific setup is included, such as browser startup and remote browser initialization.

Post-response cleanup is excluded from the timed interval where applicable.

## Run

```bash
copy .env.example .env

python -m benchmark.runner