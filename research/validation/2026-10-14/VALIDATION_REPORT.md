# Louisville price validation – 14 Oct 2026

**Result (by hand, built-in browser):** 40 live form observations, 40 match the calculated or earlier-captured price (`validation_results.csv`). Nothing was submitted: no booking, inquiry, contact, address, date or payment field was filled. The only entries were ZIP 40217 and the home-size, service and frequency selectors.

## How it was done

**Live observations.** Live form prices were observed in the Claude desktop built-in browser, which has real network access. Each observation records:
- the inputs
- the displayed Booking Summary text
- the URL
- a UTC timestamp

The raw observations are in:
- `super_cleaning_live.json`
- `red_feather_live.json`
- `maid2clean_live.json`

`compare.py` checks each observation against its comparison source and writes `validation_results.csv`. The comparison sources are:
- the 14 Oct Launch27 harvest rows (Super Cleaning)
- the site's own price feed (Maid 2 Clean)
- the 14 Oct BookingKoala harvest rows (Red Feather)

**Repeatable command.** `npm run validate:louisville` (`src/validate/louisville.ts`) runs the same checks with Playwright on a machine that has internet access. It saves the following to `output/validation/<timestamp>/`:
- `results.json` and `results.csv`
- the downloaded feeds
- screenshots

It uses the existing submission guard: booking requests are blocked and no submit buttons are clicked. It compiles and passed a mock run here. **It has not yet been run live**, because this workspace has no general internet access. Run it on the Mac to get a full screenshot set.

**Screenshots.** Two were saved: Super Cleaning P5 one-time and P5 biweekly, in `screenshots/`. Other screenshots could not be captured, because the browser pane was hidden and returns stale images while hidden. The page text and timestamps are recorded for every observation.

## Results by company

### Super Cleaning Service Louisville (Launch27)

9 of 9 match. The checks covered small, typical and larger homes (P1, P5, P9) at three service levels:

| Home | One-time | Biweekly | Deep |
|---|---|---|---|
| P1: 1 bd / 1 ba / 1–999 sq ft | $170 | $127.50 | $290 |
| P5: 3 bd / 2 ba / 1,500–1,999 sq ft | $255 | $191.25 | $395 |
| P9: 4 bd / 3 ba / 3,000–3,499 sq ft | $360 | $270 | $510 |

How the price is built:
- **Biweekly.** The form shows "Every 2 Weeks (Save 25%)" as a single booking total, and the 25% discount is applied to this first visit. It confirms the feed rule `exclude_first = false`. There is no separate recurring line.
- **Tax.** 6% sales tax is added to every total.
- **Deep.** Deep cleaning is a priced add-on to the standard service.

Together with the 3 checks from 13 Oct, there are now 12 live checks.

### Red Feather Cleaning (BookingKoala, ZIP 40217)

22 of 22 match the 14 Oct harvest.

**What the checks covered:**
- The move-out clean re-captured with the service switch confirmed in the summary.
- Bedrooms 0–5 tested one at a time, with sq ft held at 1,500–1,799.
- Bathrooms 1, 1.5, 2.5, 3 and 4 tested the same way.
- Deep and Basic priced for the same home.
- Move-out at three sq ft bands.
- Move-out with a recurring frequency selected.
- Two of the checks were made through the site's own select controls rather than by script, as a cross-check.

**Findings:**
- Move-out costs $275 before tax ($291.50 with 6% tax) for every bedroom and bathroom count. That is the same as Deep ($275). Basic costs $245 regardless of bedrooms or bathrooms.
- **Pricing depends on sq ft only.** Move-out costs $235 at 1,000–1,249 sq ft and $315 at 2,100–2,399 sq ft.
- **Move-out is one-time only.** Choosing "Every Other Week" leaves the summary on One-Time. This explains why the recurring move-out rows were unverified.
- **Correction.** The audit's rule R5, which treated "Move = Deep" as a capture artifact, was wrong for move-out. Move-out one-time rows are now included in the analysis. Construction Clean Up stays out of scope.

### Maid 2 Clean KY (Launch27)

**Why the 14 Oct harvest got 0 rows.** Discovery recorded `maidtocleanky.launch27.com`, which is the account behind the site's Login button. That account shows ACCESS DENIED, and its feed returns HTTP 403 "client is not active". The real booking page, `maid2cleanky.com/booking-page/`, embeds a different account: `smilesaremaid.launch27.com/?w_cleaning`. That account is active and was captured.

**Feed.** Pricing works like this:
- **Base price by bedroom service:** 1 bd $125, 2 bd $140, 3 bd $165, 4 bd $180, 5 bd $225.
- **Per bathroom:** $17, or $10 for 3-bedroom homes. Whole bathrooms only.
- **Sq ft bands:** 3-bed homes add $0, $15, $30, $50 or $75; 4-bed homes add $0, $15, $30 or $50.
- **Add-ons:** Deep +$50, Move +$99, plus 15 other priced extras.
- **Frequencies:** every frequency has a 0% discount.

**Live booking form.** 9 of 9 match the feed calculation:

| Home | One-time | Biweekly first visit | Biweekly recurring | Deep |
|---|---|---|---|---|
| P1 | $142 | $142 | $142 | $192 |
| P5 | $200 | $200 | $200 | $250 |
| P9 (Over 3000 sq ft) | $261 | $261 | $261 | $311 |

**Tax.** The form shows no sales-tax line.

**Discrepancies (recorded, not resolved):**
- **Homepage widget vs booking form.** The price widget on maid2cleanky.com uses a different formula from the booking form. Its rates are 130/145/190/205 plus $15 per bath, with 15%/10%/5% frequency discounts. It shows $145 vs the form's $142 (1 bd), and $220 vs the form's $200 (3 bd / 2 ba). The analysis uses the booking form.
- **Terms vs form on recurring discounts.** The terms say "weekly, semi-weekly or monthly discounts apply once your first time service is completed". The form and feed show 0% discount and the same price for first and recurring visits. Only a quote will settle this.

**Is a manual live-form price obtainable?** Yes. The booking form shows prices without contact details, so no inquiry is needed.

## Automated runs – 15 Oct 2026 (update)

**All 38 planned price checks passed across two automated runs on 15 Oct 2026 (6 in run 1, the other 32 in run 2); combinations outside that sample remain untested.**
- **Run 1** (`../2026-10-15-automated-run1/`): partial. 6 passed, 20 inconclusive, 2 errors, 10 not run.
- **Run 2** (`../2026-10-15-automated-run2/`): reran the remaining 32. All passed.
- **Expectations used:** the Launch27 sites are compared with the feed calculation from the same session; Red Feather with the by-hand observations below, used as comparison evidence only.
- **Limitation:** request bodies were not stored, so the 127 non-GET requests' contents cannot be audited - only their methods, URLs, types and sizes.

## Automated run (`npm run validate:louisville`) – NOT RUN (14 Oct evening) [superseded by the 15 Oct runs above]

The request was to run the scripted validator live on the Mac and keep its results separate from the hand checks above. It could not be run.

**Why it was blocked.** The only shell on the Mac reachable from this session is a sandboxed Linux environment with an egress allowlist:
- The competitor sites returned no connection: `supercleaning.launch27.com`, `smilesaremaid.launch27.com`, `redfeathercleaning.bookingkoala.com` and `supercleaningservicelouisville.com`.
- `registry.npmjs.org` and `github.com` were reachable.
- Playwright's browsers are not installed there.

The code was transferred and typechecks cleanly on the Mac copy (`npx tsc --noEmit`). macOS Terminal itself can't be driven from this session.

**To run it**, in Terminal on the Mac:
```
cd ~/Documents/Workspace/Projects/cleaning-company
npx playwright install chromium   # only if Edge/Chrome is not installed
npm run validate:louisville
```

**Output.** Results land in `output/validation/<timestamp>/`. That folder is git-ignored; copy it to `research/validation/<date>-automated/` to keep it.

**How the two sets of results are kept apart.** Everything in this folder so far is labelled "built-in browser (by hand)". Automated results must be labelled "Playwright (`validate:louisville`)" and compared against these, not merged into them.

**Discrepancies.** Investigate any mismatch before changing an expected value. The validator flags `NO (diff …)` and keeps the raw panel text and screenshot for each check.

## Feed-derived vs live-verified (after this validation)

| Company | Evidence tier now | Live checks |
|---|---|---|
| Scrub Lou | live form observation (all rows) | n/a – every row is a live observation |
| Maids in Apron | live form observation; deep/move = model from live add-on checks | 13 Oct checks |
| Red Feather | live form observation | 22 re-checks, 14 Oct |
| Super Cleaning | booking-platform feed calculation | 12 (13–14 Oct), all matched |
| Maid 2 Clean | booking-platform feed calculation (modelled from the saved feed) | 9 (14 Oct), all matched |
| Peer-city Launch27 companies | booking-platform feed calculation | none |

## Not covered

- Prices at other Louisville ZIPs. Only ZIP 40217 was tested.
- Fees shown only after a date or time is chosen, if any exist. Selecting a date was avoided.
- Scrub Lou and Maids in Apron were not re-checked today. Their 13 Oct and 14 Oct captures were already identical, 5,220 of 5,220 rows for Scrub Lou.
