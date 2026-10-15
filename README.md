# cleaning-price-research

Local TypeScript + Playwright tool that collects comparable residential cleaning quotes and saves the evidence: inputs, form selections, price breakdown, a screenshot and a timestamp.

**Goal:** collect as much Louisville competitor pricing as possible to build a pricing matrix for setting our own prices, plus the same full price grids from peer cities (Lexington, Cincinnati, Indianapolis, Nashville, Columbus, …) to see how the market structures prices.

## One command: collect everything

```bash
npm install
npm run collect
```

This runs unattended, with no manual steps:
1. **Discover**: for every city in `config/cities.json`, searches the web for cleaning companies, opens each website, and detects which ones show an instant online price (BookingKoala or Launch27 booking forms, including ones on the company's own domain). Harvestable ones are added to `config/companies.discovered.json`. Every site checked is listed in `output/discovery/<date>.csv`, including lead-form-only sites.
2. **Harvest**: walks every service × frequency × bedrooms × bathrooms × sq ft combination on every known form. It enters the city's ZIP only where the form has a ZIP field. In the 14 Oct run, 10 of 19 BookingKoala forms had none, so they priced at the default location. Launch27 feeds ignore ZIP entirely. Form labels are detected automatically. A site that fails is logged and skipped, and the run continues. Each run is logged in `output/harvest/_runs/<date>.csv`. Note: the completed 14 Oct run used code compiled before the 14 Oct harvester fixes (per-company time cap, skipping unoffered service/frequency pairs, Launch27 size-only expansion), so those fixes did not apply to it. See `research/analysis/2026-10-14/AUDIT_REPORT.md` (A5, A9).
3. **Build**: `research/build_market.py` writes `research/market/<date>/`: `market_matrix.csv` (every combination, same columns as the 13 Oct `full_matrix.csv` plus `city`), `profiles.csv`, `city_index.csv`, `structure.csv` and `Market_Price_Matrix.xlsx`. **Known bug:** its profile lookup mis-prices bedroom-named Launch27 services, and it marks Launch27 rows as verified. Do not use `research/market/2026-10-14/` for decisions. Use the audited outputs in `research/analysis/2026-10-14/` (`bash research/analysis/2026-10-14/scripts/run_all.sh`).

Useful variations:
```bash
npm run collect -- --city cincinnati     # one city only
npm run collect -- --no-discover         # re-price everything already known (monthly refresh)
npm run discover -- lexington            # discovery only
npm run harvest -- all --city nashville  # harvest only
npm run build-matrix                     # rebuild the workbook from saved harvests
```
A full run over 18 cities takes a few hours (mostly the live BookingKoala grids). Re-running is safe: companies already harvested today are skipped.

**Reading the peer-city data:** peer-city samples are 1–4 companies per city, found by search. Treat them as examples of pricing structure (frequency discounts, deep and move-out premiums, $ per bedroom, bath and sq ft), not as market levels. Use the **Peer Structure** sheet of `research/analysis/2026-10-14/Louisville_Comparison_Validated.xlsx`. The City Index in `research/market/2026-10-14/` came from the buggy build.

## Current data (14 Oct 2026)

Start with these:
- **`research/analysis/2026-10-14/`**: the audited analysis. Read `FINDINGS.md` first, then `Louisville_Comparison_Validated.xlsx` and `AUDIT_REPORT.md`.
  - 294,901 raw rows → 172,339 analytical rows.
  - 27 usable harvested companies in 14 cities, plus Maid 2 Clean.
  - Louisville has five instant-price companies: Scrub Lou, Maids in Apron, Super Cleaning, Red Feather and Maid 2 Clean. Alongside them are the R&R formula and published lists from Stitch, Cleanoria, LouBelle, Your Cleaning Krew, Busy Brooms and Hello Cleaners.
  - Red Feather has an instant BookingKoala calculator. It is not lead-form-only, as the 13 Oct notes said.
  - **Comparison basis:** same home, same service, same visit type.
    - Scrub Lou, Super Cleaning and Red Feather add 6% tax at checkout and are shown pre-tax; Maids in Apron's tax-inclusive total is divided by 1.06.
    - Maid 2 Clean: **no tax displayed; treatment unconfirmed**.
    - The 3 bd / 2 ba / 1,600 sq ft standard one-time median is $245 pre-tax (n=5), $247 without Maid 2 Clean, and $259.70 on a customer-pays basis. See the workbook's **Five-Company Basis** sheet.
  - **Sampled live verification vs untested combinations:**
    - Scrub Lou, Maids in Apron and Red Feather cells are live form observations.
    - Super Cleaning and Maid 2 Clean cells are calculated from the price table the booking form downloads; only 12 and 9 of their combinations were checked live, and the rest are untested.
- **`research/validation/2026-10-14/`**: Louisville live price validation, done by hand in the built-in browser with no submissions. 40 of 40 observations matched (`VALIDATION_REPORT.md`). Scripted runs: see `research/validation/2026-10-15-automated-run1/` and `-run2/`.
- **`research/checklists/2026-10-14/`**: published service checklists for 17 companies, all captured verbatim. Includes a task × company matrix coded included / excluded / paid extra / conditional / not stated (`CHECKLIST_FINDINGS.md`).
  - The first version's corrected cells are listed in `corrections_vs_first_version.csv`.
  - Hello Cleaners, a national platform, is excluded from Louisville conclusions.
  - Stitch's Louisville identity was verified with the Kentucky Secretary of State.
- **`research/our-offering/2026-10-14/STANDARD_CLEAN_CHECKLIST_DRAFT.md`**: first draft of OUR standard-clean checklist. For each task it gives cleaner instructions, customer wording, condition limits and time-trial flags. All prices are provisional (TBD).
- **`research/quote-requests/2026-10-14/`**: quote requests for MaidPro, Merry Maids, The Maids, The Cleaning Authority and Maid in the Ville. They are prepared but **not submitted**, and are waiting for the home details listed there.

These older snapshots are kept unchanged as raw evidence:
- `research/2026-10-13/`: the 13 Oct workbook and `full_matrix.csv` (22,488 rows).
- `research/market/2026-10-14/`: superseded, see the note above.

## Validate Louisville prices

```bash
npm run validate:louisville
```

**Status (15 Oct):** All 38 planned price checks passed across two automated runs on 15 Oct 2026 (6 in run 1, the other 32 in run 2); combinations outside that sample remain untested.
- **Run 1** (`research/validation/2026-10-15-automated-run1/`): partial. Launch27 stopped when the service change rebuilt the form, and Red Feather prices failed to parse (an icon-font "$"). Both are fixed.
- **Run 2** (`research/validation/2026-10-15-automated-run2/`): reran the 32 checks that didn't pass in run 1. All passed.
- **Network:** request bodies were not stored, so the 127 non-GET requests' contents cannot be audited - only their methods, URLs, types and sizes. None of the 127 were unexpected after review: 34 were first-party price, slot and config calls, 93 known third-party scripts (Stripe, hCaptcha, Google Analytics, Drift, Bugsnag).
- **Re-running:** run it in your own Terminal. Re-run only checks that didn't pass with `npm run validate:louisville -- --rerun <run folder>`, or pick checks with `--only <ids>`.
- Keep automated results separate from the by-hand checks in `research/validation/2026-10-14/`.

This re-checks Louisville prices on the live forms. It covers:
- **Red Feather:** move-out re-capture, bedrooms and bathrooms tested one at a time at a fixed sq ft, deep vs basic, and move-out with a recurring frequency.
- **Maid 2 Clean:** checks the old feed host for the blocker, reads the homepage widget, and finds the live booking iframe.
- **Launch27 spot checks:** Super Cleaning and Maid 2 Clean, on small, typical and larger homes × one-time standard, biweekly and deep.

It records every input, displayed price, URL, timestamp and screenshot. For the Launch27 checks it compares each observed price with the price calculated from the site's feed and lists any discrepancy. BookingKoala sites have no feed, so Red Feather observations are recorded and then compared with the harvest; `research/validation/2026-10-14/compare.py` shows how. Results go to `output/validation/<timestamp>/` (`results.json`, `results.csv`, `screenshots/`, `<site>_feed.json`). The submission guard stays on, and contact fields are never filled.

## Setup

```powershell
cd C:\Users\ccarrigan.LMLAWFIRM\source\repos\Data_Collection_Clean\cleaning-price-research
npm install
```

By default the tool drives your installed **Microsoft Edge** (`"channel": "msedge"` in `config/settings.json`). If Edge isn't installed it falls back to Chrome, then to Playwright's Chromium. To use Playwright's bundled Chromium instead, set `"channel": "chromium"` and run `npx playwright install chromium`. You can also set `BROWSER_CHANNEL=chrome` (or `chromium`) for a single run.

## Commands

```powershell
npm run harvest -- all                # refresh the full price grid for every configured competitor
npm run harvest -- maids-in-apron     # one competitor (set $env:ZIP="40205" to price another ZIP)
```
Harvest output: `output/harvest/<company>/<date>.csv` (+ `.json`). Each BookingKoala row is marked `verified` only when the site's Booking Summary shows exactly the selected options.

```powershell
npm run open                       # Step 1: visible browser at Scrub Lou's quote page
npm run quote                      # Step 3: baseline quote (medium home, one-time standard)
npm run quote -- --profile large --scenario oven
npm run quote -- --keep-open       # leave the browser open to compare against the screen
npm run list                       # companies, profiles, scenarios
npm run export-csv                 # rebuild output/quotes.csv from all saved JSON
```

Each quote writes:
- `output/quotes/<runId>.json`: the full record (requested settings, actual form selections, price breakdown, terms, evidence, network log)
- `output/evidence/<company>/<runId>.png` and `<runId>__price.png`: a full-page screenshot and a close-up of the price panel
- `output/quotes.csv`: a flattened export for Excel, rebuilt after every capture

## Statuses
| Status | Meaning |
|---|---|
| `success` | Price captured, and the site's summary matches our selections |
| `manual_quote_required` | No online price for these inputs (home too large, ZIP not served, …) |
| `verification_required` | CAPTCHA, login or code prompt. In an interactive terminal the run pauses so you can solve it. |
| `unsupported_option` | The site doesn't offer the requested frequency or extra |
| `not_implemented` | The site supports the option but the adapter can't do it yet (Scrub Lou partial home) |
| `extraction_failed` | The price didn't settle, or the summary didn't match our selections |
| `error` | Unexpected failure. A screenshot is still saved. |

An unavailable price is never recorded as $0, and undisclosed amounts are left blank.

## Safety
- No booking, payment or subscription is ever submitted (`safety.allowSubmission: false`).
- Adapters never fill contact, address, date or card fields, and never click submit buttons.
- A network guard aborts POSTs that match booking, lead, customer or Stripe payment endpoints. Every non-GET request is logged in the JSON record under `evidence.networkPosts`.
- Each run uses a fresh browser profile, so no cookies or sessions are kept.
- `output/`, `.env`, browser data and `config/*.local.json` are git-ignored. Use `researching4clean@gmail.com` (in `config/settings.json`) wherever a form requires contact info.

## Layout
```
src/
  discover/      web search + booking-platform detection (discover.ts)
  harvest/       full-grid harvesters for BookingKoala and Launch27 forms
  adapters/      one automation script per competitor (scrubLou.ts)
  scenarios/     home profiles (ZIP 40217, no pets) and the six controlled scenarios
  capture/       browser launch + submission guard, price parsing/waiting, screenshots, CAPTCHA pause
  storage/       JSON records and CSV export
  types.ts       shared quote data format
  index.ts       command-line entry point
config/          company URLs, cities, discovered companies, research settings
docs/            form inspection notes (scrub-lou-form-notes.md)
output/          captured quotes and evidence (git-ignored)
```

## Rebuilding the matrix workbook
`research/2026-10-13/build.py` turns the three pricing models (`*_model.json`) into `full_matrix.csv` + `matrix.json`, and `workbook.py` writes the Excel file (Python 3 with numpy and openpyxl).

## Adding cities or companies
- Cities: add `{ "id", "name", "state", "zip" }` to `config/cities.json`. Use a middle-income residential ZIP.
- Companies: discovery fills `config/companies.discovered.json`. Hand entries go in `config/companies.json` with `"city"` (and optionally `"zip"`) and take priority. Delete a line from the discovered file to drop a company.


## Pilot timing sheet
`research/our-offering/2026-10-14/build_pilot_timing_sheet.py` builds the blank, printable `PILOT_TIMING_SHEET.pdf` that goes with `STANDARD_CLEAN_CHECKLIST_v5.md`. To regenerate it:
```powershell
cd research\our-offering\2026-10-14
pip install -r requirements.txt
python build_pilot_timing_sheet.py
```

## Next steps
- Run `npm run validate:louisville` on a machine with internet access to get the full screenshot set.
- Send the five prepared quote requests once the home profile is confirmed (`research/quote-requests/2026-10-14/QUOTE_REQUESTS.md`), and log the replies in that folder. Other lead-form-only companies seen 13 Oct: 502 Star Services, Deep Blue Clean.
- Add calculators for Your Cleaning Krew (booking.yourcleaningkrew.com) and Louisville Cleaning Pros (louisvillecleaningpros.com/book).
- Point discovery at a site's embedded booking iframe, not its Login link. Maid 2 Clean failed because the recorded Launch27 host was an inactive account.
- Re-run `npm run harvest -- all` monthly to track price changes.
