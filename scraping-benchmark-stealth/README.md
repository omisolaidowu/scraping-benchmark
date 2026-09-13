# Stealth Scraping Benchmark

A companion benchmark to the primary scraping benchmark. It uses the same target environments, extraction rules, validation logic, timeout, latency measurement, and raw evidence capture, but evaluates the approaches using their documented stealth-oriented configurations.

This benchmark should be treated as a separate configuration experiment. Results are not combined with or used to replace the primary benchmark results.

## Approaches

### Firecrawl

Uses the Firecrawl Scrape API with `proxy="enhanced"`. Firecrawl's documentation describes enhanced proxies as the higher-resistance option for complex sites; this is the provider's API-level stealth-oriented configuration rather than a browser-level stealth switch.

### Browserless

Uses the REST `/unblock` endpoint with:

- `stealth=true`
- `proxy=residential`
- `content=true`

Browserless documents `stealth` as a launch parameter for REST APIs and recommends combining stealth with a residential proxy for bot-protected sites.

### Surfsky

Uses Surfsky's cloud browser over CDP with Patchright, following Surfsky's recommendation to use a patched browser automation framework such as Patchright or rebrowser-playwright for bot-protected sites.

The profile also enables Surfsky's documented anti-captcha system and automatic solving for supported challenges where applicable.

### SeleniumBase

Uses SeleniumBase UC Mode with `uc=True` and headless Chromium.

UC Mode is treated as SeleniumBase's expected anti-detection configuration. No additional stealth configuration is introduced for SeleniumBase in this category.

## Methodology

The benchmark is deliberately comparable to the primary benchmark but should be treated as a separate configuration experiment.

The main question is not whether these providers can scrape the targets at all, but how their documented stealth-oriented configurations affect success and latency relative to the primary benchmark.

Run a 2-run smoke test first. If the configuration and extraction are sound, run the definitive benchmark using the configured number of iterations.

The same number of runs is applied consistently across all approach × target combinations.

Do not replace the primary benchmark results with these results. Analyze the two configurations separately.

## Success Criteria

A run is considered successful only when the expected target data is successfully retrieved and passes the benchmark's extraction validator.

HTTP status codes, provider success responses, or CAPTCHA/Turnstile solver signals alone do not constitute a successful scrape.

## Timing

Elapsed time starts immediately before the approach execution and ends when usable target HTML is returned.

Approach-specific setup is included, such as Surfsky profile creation and remote browser startup.

Post-response cleanup is excluded from the timed interval where applicable.

## Run

```bash
copy .env.example .env

python -m benchmark.runner