# Automated run 1 – `npm run validate:louisville`, 15 Oct 2026 13:48–13:51 UTC

**Verdict: partial run. It does not validate all three companies.**
- Launch27 (Super Cleaning, Maid 2 Clean): only the small-home checks ran. Both sections stopped at the first check after the service changed.
- Red Feather: every check ran, but the validator recorded no prices, so its own conclusions ("sq ft: false" and the rest) are invalid.

Where things are:
- `original/`: the run's files, copied unchanged. They are verified against `ORIGINAL_SHA256.txt`. The source copy is still in `output/validation/2026-10-15-13-48-53/`.
- `check_status.csv` and `summary.json`: derived after the run by `analyze_run1.py`.
- The terminal log you pasted was not received in this session. This analysis therefore uses the saved files only; the files don't include the Playwright call log.

## 1. Check accounting (price checks are kept separate from discovery observations)

| | Count |
|---|---|
| Price checks planned | 38 (Red Feather 20 + Launch27 18) |
| Completed (reached a result) | 26 |
| **Passed** | **6**: Launch27 small home × one-time / biweekly / deep, for Super Cleaning and Maid 2 Clean |
| Failed (price mismatch) | 0 |
| **Inconclusive** | **20**: every Red Feather check; the validator recorded `total_before_tax = null` |
| **Error** | **2**: `l27-super-typical-one`, `l27-m2-typical-one` (`locator.evaluate: Timeout 30000ms exceeded`) |
| **Not run** | **10**: the remaining typical and larger-home Launch27 checks, after each section stopped |
| Discovery observations (not price checks) | 8: the Maid 2 Clean old host returned 403 "client is not active"; the booking-page iframe is on `smilesaremaid.launch27.com`; 6 homepage-widget readings |

The run's closing line, "0 discrepancies", counted only rows marked `NO`. That hid 2 errors, 10 checks that never ran and 20 checks with no price.

## 2. Launch27 timeouts (Super Cleaning and Maid 2 Clean)

**Where it failed.** Both sections failed at the same point: the first check of the typical home (`Three Bedroom Home`), right after the small-home checks passed.

**Iframe targeting: not the cause.** The validator opens the Launch27 booking URL directly as the page, so no frame needs to be targeted.

**Element availability: the cause.** Tested in the built-in browser on both forms (choosing options only; nothing submitted):
- Both forms open on `One Bedroom Home`. The small-home checks therefore never changed the service.
- Changing the service to `Three Bedroom Home` **re-renders every `<select>` on the form**. The previously selected element is detached: `isConnected = false`, and none of the 4 select elements is the same node afterwards.
- The validator's `l27Select` marked the select with `data-validate-target`, chose the option, then ran `loc.evaluate(removeAttribute)` on `select[data-validate-target="1"]`. After the re-render no element carries that marker, so Playwright waited 30 s and threw `locator.evaluate: Timeout 30000ms exceeded`.

**Page readiness: also a gap.** The old code never waited for the dependent selects to be rebuilt, or for the price estimate request to return, before reading the panel.

**Fix (no timeout lengthened):**
- Each select is found fresh by the option text it offers, with no marker or stored handle.
- Each choice is confirmed by re-reading the visible selects.
- The price is read only after the form's `POST /v1/booking/estimate_price` returns with nothing still in flight, then the panel stays unchanged for 2 s.
- Each check is isolated, so one failure no longer stops the rest.

## 3. Red Feather "sq ft: false" (and the other "false" results)

| Question | Finding |
|---|---|
| Exact inputs | ZIP 40217; Move In/Out Clean; One-Time; 3 bd / 2 ba; Sq Ft `1000-1249 Sq Ft`, then `2100-2399 Sq Ft` (`rf-move-sq1000` at 13:49:53Z, `rf-move-sq2100` at 13:49:56Z) |
| Observed prices (this run's own saved Booking Summary text) | **$235.00** before tax / $249.10 total, and **$315.00** / $333.90 |
| Why "false" was printed | The Booking Summary shows the dollar sign as an icon-font glyph (U+F155): `Total Before Tax 315.00`. The pattern `Total Before Tax ([\d.,]+)` needs a digit right after the space, so every price parsed as null. The "does the price vary?" test then compared {null, null} and printed `false`. The same applies to the bedroom and bathroom results; they are invalid, not evidence of a flat price. |
| Did the selection change? | Yes. In all 20 rows, the summary text shows the requested service, bedrooms, bathrooms and sq ft. The one exception is `rf-move-eow`, where the frequency stayed One-Time; that is the expected finding (recurring move-out isn't offered). |
| Did the price finish updating? | Yes. The surviving screenshot shows 2100-2399 Sq Ft with $315.00 / $333.90, matching the text. Prices change between consecutive checks (e.g. 245 → 235), so they were not stale. This form computes prices in the page: changing selections sends no network requests (checked in the built-in browser). |
| Price-band boundary? | The two tests use different bands, `1000-1249` and `2100-2399`; the 1,500–1,799 reference sits between them. Each is a separate band, so a different price is expected; no test sat on a band edge. |
| Compared with the 14 Oct by-hand observations (comparison evidence only) | All 20 re-parsed prices match: 235 / 275 / 315 for the three sq ft bands, 275 for move-out at every bed and bath count, 245 for basic. |
| Screenshot problem | Both sq ft checks wrote the same file name, so the `1000-1249` screenshot was overwritten. Only the `2100-2399` image survives. |

These re-parsed prices come from this automated run's own captured text. Even so, the checks stay **inconclusive** in the run's record, because the validator itself didn't produce them. They are in the rerun.

## 4. The 107 non-GET requests

**What the run saved.** Only the count. The guard logged method and URL in memory, but the validator wrote only "107 non-GET requests logged". The run's files therefore **cannot show** whether any request was unexpected. Zero blocked requests proves only that none matched the block patterns.

**What these pages normally send.** Comparison only, from the built-in browser on the same three pages:
- **Red Feather (BookingKoala), at page load:**
  - `POST /cdn-cgi/rum` (Cloudflare analytics)
  - `POST /api/v4/form-custom-fields` (form configuration read)
  - `POST /api/v7/addons/search` (add-on list read)
  - `POST /leads/v1/pages/popups` (popup configuration; deliberately not blocked)
  - Changing the price selections sends **no** requests.
- **Launch27 (both sites):** every selection change sends `POST /v1/booking/estimate_price` (price for the current selections) and `POST /v1/booking/spots` (time-slot lookup). The booking-creation endpoint (`/v1/booking`) matches the guard's block pattern.
- **Not checked:** the maid2cleanky.com homepage and booking page.

**Is 107 plausible?** About 9 Launch27 selection changes × 2 requests × 3 checks per site, plus page loads, is consistent with 107. But consistency isn't proof.

**Fix.** Every non-GET request is now saved to `network_requests.json`, with time, method, URL (query string removed, as before), resource type, the page it came from, and body size and type (no body contents). Each is classified as expected (the list above), blocked, or **UNEXPECTED – review**. The summary reports the unexpected count.

## 5. Other validator fixes

- Price parsing tolerates icon-font or `$` currency symbols before the digits, in both form types.
- Every planned check has an id and one status: passed / failed / error / inconclusive / not_run / observation. They are written to `summary.json` and to the results files, and the console prints each count. Failed, error and inconclusive checks are listed by name.
- Red Feather readiness: the price is read only after the summary shows every requested selection, then stays unchanged for 1.5 s.
- Red Feather pass/fail compares against the 14 Oct by-hand observations (`research/validation/louisville_expected.json`). These are labelled as comparison evidence, because BookingKoala has no price feed to calculate from. Launch27 pass/fail is against the feed calculation from the same session, with the by-hand value shown alongside.
- The structure conclusions ("bedrooms change the price?") use passed checks only; otherwise they print `inconclusive`.
- Screenshot names are the check id, so they are unique.
- New options: `--only <ids or prefixes>` and `--rerun <folder with summary.json>`.

The fixed validator was run live in run 2 (`../2026-10-15-automated-run2/`). All 32 rerun checks passed, so all 38 planned price checks have now passed across the two runs. Combinations outside that sample remain untested.

## 6. Rerun only the failed or inconclusive checks

This reruns 32 checks: 20 Red Feather, 6 Super Cleaning (typical and larger) and 6 Maid 2 Clean (typical and larger). The 6 passed checks and 8 discovery observations are skipped:

```
cd ~/Documents/Workspace/Projects/cleaning-company
npm run validate:louisville -- --rerun research/validation/2026-10-15-automated-run1
```

Equivalent explicit form:

```
npm run validate:louisville -- --only rf,l27-super-typical,l27-super-larger,l27-m2-typical,l27-m2-larger
```
