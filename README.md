# cleaning-price-research

Local TypeScript + Playwright tool that collects comparable residential cleaning quotes and saves the evidence: inputs, form selections, price breakdown, a screenshot and a timestamp.

**Goal:** collect as much Louisville competitor pricing as possible to build a pricing matrix for setting our own prices.

**Current data (13 Oct 2026):** see `research/2026-10-13/Louisville_Cleaning_Price_Matrix.xlsx`
- Scrub Lou: full grid, 5,220 live form combinations
- Maids in Apron: full grid, 7,056 live combinations plus deep/move add-ons and extras
- Super Cleaning Service: full price table from their booking feed, spot-checked on the live form
- Rocking Robins (R&R) Maids: full calculator formula (hours × $60) from their booking page
- Round 1 tracker (10 companies) and platform sample (Taskrabbit, Thumbtack, Homeaglow, Angi, Care.com, Craigslist) on the Round 1 Tracker / Platforms sheets
- Published price lists: Stitch Cleaning, Cleanoria (Thumbtack), LouBelle ($40/hr per tech), Your Cleaning Krew, Busy Brooms, Hello Cleaners
- 22,488 normalized price rows in `full_matrix.csv`, and a side-by-side comparison on 19 common home profiles

## Setup (Windows, VS Code)

```powershell
cd C:\Users\ccarrigan.LMLAWFIRM\source\repos\Data_Collection_Clean\cleaning-price-research
npm install
```

By default the tool drives your installed **Microsoft Edge** (`"channel": "msedge"` in `config/settings.json`), so you don't have to download a browser. To use Playwright's bundled Chromium instead, set `"channel": "chromium"` and run `npx playwright install chromium`. You can also set `BROWSER_CHANNEL=chrome` (or `chromium`) for a single run.

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
  adapters/      one automation script per competitor (scrubLou.ts)
  scenarios/     home profiles (ZIP 40217, no pets) and the six controlled scenarios
  capture/       browser launch + submission guard, price parsing/waiting, screenshots, CAPTCHA pause
  storage/       JSON records and CSV export
  types.ts       shared quote data format
  index.ts       command-line entry point
config/          company URLs and research settings
docs/            form inspection notes (scrub-lou-form-notes.md)
output/          captured quotes and evidence (git-ignored)
```

## Rebuilding the matrix workbook
`research/2026-10-13/build.py` turns the three pricing models (`*_model.json`) into `full_matrix.csv` + `matrix.json`, and `workbook.py` writes the Excel file (Python 3 with numpy and openpyxl).

## Next steps
- Add calculators for R&R Maids (rrmaids.com/book-house-cleaning), Your Cleaning Krew (booking.yourcleaningkrew.com) and Louisville Cleaning Pros (louisvillecleaningpros.com/book).
- Request quotes by hand from lead-form-only companies (The Maids, MaidPro, 502 Star, Deep Blue Clean, Red Feather), using researching4clean@gmail.com, and log the follow-up messages.
- Re-run `npm run harvest -- all` monthly to track price changes.
