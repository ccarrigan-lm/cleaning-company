# Automated run 2 – `--rerun` of run 1, 15 Oct 2026 14:08–14:11 UTC

**Result: All 38 planned price checks passed across two automated runs on 15 Oct 2026 (6 in run 1, the other 32 in run 2); combinations outside that sample remain untested.**
- **Run 2:** 32 checks passed. These are all 20 Red Feather checks, plus the typical- and larger-home checks for Super Cleaning (6) and Maid 2 Clean (6). There were 0 failures, 0 inconclusive, 0 errors and 0 not run.
- **Run 1:** the other 6 checks (the small-home Launch27 checks) passed then. Run 2 didn't repeat them, so they show as "not run" there.

Combined status is in `combined_status.json`. Original files are in `original/`, verified against `ORIGINAL_SHA256.txt`.

## What the evidence is

- **Super Cleaning and Maid 2 Clean.** Each price was observed on the live form in this run and equals the price calculated from the site's own price table, downloaded in the same session. Each also equals the 14 Oct by-hand value.
- **Red Feather.** BookingKoala gives no price table to calculate from, so a "pass" here means the price this run observed equals the 14 Oct by-hand observation. Before reading, the run checked that the Booking Summary showed every requested selection.
- **Red Feather pricing structure**, from passed checks only:
  - Bedrooms 0–5 don't change the price.
  - Bathrooms 1–4 don't change the price.
  - Square footage does: $235 / $275 / $315 for the 1000–1249, 1500–1799 and 2100–2399 sq ft bands.
  - Move-out is offered as one-time only.
- **Discovery observations** (Maid 2 Clean's old host, its iframe and the homepage widget) weren't selected for this rerun. They come from run 1.
- **Still untested:** combinations outside these 38 checks.

## The 127 non-GET requests

| Group | Count | What it is |
|---|---|---|
| Launch27 price estimate and time-slot lookups | 29 | Super Cleaning 13, Maid 2 Clean 16 |
| BookingKoala page-load config reads and Cloudflare beacon | 5 | Red Feather |
| Stripe.js telemetry | 61 | Red Feather 28, Super Cleaning 33. Both forms embed a Stripe card field; nothing was typed into it. |
| Stripe fraud-detection fingerprint | 11 | |
| Stripe wallet config | 3 | |
| hCaptcha widget load and challenge fetch | 6 | Red Feather 2, Super Cleaning 4. The largest bodies, about 26 KB each, are hCaptcha's encoded environment data. The challenge wasn't solved. |
| Google Analytics / DoubleClick | 7 | |
| Drift chat widget | 3 | Maid 2 Clean |
| Bugsnag error reporting | 2 | Red Feather |

**None were unexpected after review, and none were blocked.** The only competitor hosts that received POSTs were the three booking-form hosts, at the price, slot and config endpoints above. No booking-creation endpoint was called.

Request bodies weren't stored, so the body contents can't be audited. What the run itself entered was the ZIP code and the price selections only.

**Classifier update.** The validator now labels these known third-party scripts as THIRD-PARTY rather than UNEXPECTED. Anything new is still flagged UNEXPECTED.
