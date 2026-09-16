# Turnstile Login Scraping Benchmark

A separate benchmark for evaluating how the scraping approaches handle an interactive login workflow protected by Cloudflare Turnstile.

Unlike the standard and stealth benchmarks, this test requires each approach to complete the login workflow before the target data can be extracted. The benchmark therefore evaluates the complete workflow rather than simply retrieving the login page.

## Approaches

### Firecrawl

Uses the Firecrawl Scrape API with `proxy="enhanced"` to establish the session, followed by Firecrawl's interactive `interact()` workflow.

The interaction enters the configured credentials, submits the login form, verifies the authenticated URL, and returns the authenticated page HTML for extraction and validation.

### Browserless

Uses the Browserless BrowserQL `/stealth/bql` endpoint with:

- `proxy="residential"`
- `humanlike=true`
- `proxyLocaleMatch=1`

The BrowserQL workflow:

1. Navigates to the login page.
2. Waits for the Turnstile-protected form.
3. Uses Browserless's Cloudflare solver.
4. Enters the configured credentials.
5. Submits the form.
6. Waits for the authenticated content.
7. Verifies that the final URL contains the expected dashboard path.
8. Returns the full page HTML for extraction and validation.

### Surfsky

Uses Surfsky's cloud browser with the Turnstile login workflow defined in the target configuration.

The workflow must complete the login process and reach the authenticated dashboard before the returned page is passed to the same extraction and validation process used by the other approaches.

### SeleniumBase

Uses SeleniumBase UC Mode with headless Chromium and the Turnstile login workflow.

The approach must complete the login process and reach the authenticated dashboard before the returned page is passed to the extraction and validation process.

## Methodology

This benchmark is treated separately from the standard and stealth scraping benchmarks because the target requires an interactive, authenticated workflow.

Each approach is tested against the same Turnstile login page using the same credentials, target selectors, extraction rules, and validation criteria.

Run a 2-run smoke test first. If the configuration and workflow are sound, run the definitive benchmark using the configured number of iterations.

The same number of runs is applied consistently across all approaches.

## Success Criteria

A run is considered successful only when the approach:

1. Successfully handles the Turnstile-protected login workflow.
2. Reaches the expected authenticated dashboard.
3. Returns the target page content.
4. Extracts the expected records.
5. Passes the benchmark's extraction validator.

A successful HTTP response, a solver success signal, or reaching the login form alone does not constitute a successful run.

## Timing

Elapsed time starts immediately before the approach execution and ends when the authenticated target HTML is returned.

This includes the time required to load the login page, handle the Turnstile workflow, submit the credentials, reach the authenticated page, and return the HTML.

Post-response cleanup is excluded from the timed interval where applicable.

## Run

```bash
copy .env.example .env

python -m benchmark.runner