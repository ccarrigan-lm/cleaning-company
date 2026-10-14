# Audit report: cleaning price research (13–14 Oct 2026 collection)

Audit date: 14 Oct 2026. Scope: every file in the repository plus the raw Launch27 feeds kept on the Mac (`output/harvest/*/_raw-feed.json`, not in git). Originals were not modified. No web collection was restarted; no inquiries, bookings or messages were sent.

> **Addendum – 14 Oct 2026, after live validation.** This report has been updated after the Louisville live checks in `research/validation/2026-10-14/`. Those checks found 40 of 40 observations matched.
>
> What changed:
> - **Rule R5 reversed for Red Feather Move In/Out.** Move-out really is priced the same as deep cleaning, and pricing depends on sq ft only. Move-out is offered one-time only.
> - **Red Feather move-out rows re-included.** 1,092 rows were added, so the analytical table now has 172,339 rows, up from 171,247.
> - **Maid 2 Clean KY added.** It is modelled from its live booking feed and matched 9 live checks. The harvest had used an inactive Launch27 host.
> - **Super Cleaning now has 12 live checks.**
> - **Included-task checklists captured** for 17 Louisville companies, in `research/checklists/2026-10-14/`.
> - **Issues updated:** A3 and A21 are resolved, A22 (validation) is added, and a correction is logged.
>
> Struck-through items below are kept so the original findings stay on record.

Outputs of this audit live in `research/analysis/2026-10-14/`:

| File | What it is |
|---|---|
| `AUDIT_REPORT.md` | This report |
| `FINDINGS.md` | Concise findings for pricing decisions |
| `Louisville_Comparison_Validated.xlsx` | Validated comparison workbook (15 sheets incl. sources, issues, rules, data dictionary) |
| `data/observations_normalized.csv.gz` | All 294,901 raw rows, normalized, with include flag, rule ids and `source_file`/`source_row` |
| `data/analytical_prices.csv.gz` | 172,339 included, de-duplicated rows (171,247 before the 14 Oct R5 correction) |
| `data/profile_prices_all.csv` | Every company priced on 10 home profiles × 6 service/frequency cases (corrected lookup) |
| `data/structure_by_company.csv` | Price-change metrics per company |
| `data/companies.csv`, `price_availability.csv`, `city_coverage.csv`, `extras.csv`, `scope.csv`, `rule_counts.csv`, `old_profiles_recheck.csv` | Supporting tables |
| `scripts/` | `load_raw.py` → `normalize.py` → `analyze.py` → `build_tables.py` → `build_workbook.py` (rerunnable) |

---

## 1. Which outputs are current

| Output | Date | Status |
|---|---|---|
| `output/harvest/*/2026-10-14-00-52-02*.csv` + run log `_runs/2026-10-14-00-52-02.csv` | 14 Oct (run 00:52–17:01 UTC) | **Latest completed collection.** Raw records; preserved. |
| `research/market/2026-10-14/*` (market_matrix, profiles, city_index, structure, workbook) | 14 Oct 17:10 | Built from the latest collection but **contains a pricing-lookup bug and mislabelled evidence** (§3). Superseded by this audit. |
| `research/2026-10-13/*` (3 models, R&R and Cleanoria models, full_matrix, comparison, workbook) | 13 Oct | **Older snapshot.** Still the only source for R&R, Cleanoria, Stitch and the other published Louisville prices, and for Maids in Apron's deep and move-out add-ons. Its three harvested models agree with the 14 Oct captures (§4). |
| `README.md` | 13–14 Oct | Partly stale (§7). |

The completed run used the code compiled when it started (00:52 UTC). The fixes made that morning (45-minute cap per company, skipping service/frequency pairs a form doesn't offer, Launch27 size-only expansion, ignoring home-access dropdowns) were **not in effect** for this run, although the README describes them.

## 2. Usable coverage

| | Count |
|---|---|
| Websites checked by discovery | 244 visits, 170 distinct domains, 18 cities |
| Harvest attempts | 38 companies |
| **Usable instant-price companies** | **27** (4 Louisville + 23 in 12 peer cities). Bear Bros and Rapids are partial |
| Excluded after capture | 4: Deluxe Maid and Better Cleans (identical template prices), Fresh Space (Cleveland, not Columbus), Kindly Cleaners (demo form) |
| Failed / removed | 7: Maid 2 Clean KY, Patriot Maids, St. Louis Clean Solutions (0 rows); HomeTown Clean, The Valley Clean Team, Maggy Maid, Spruced Up Cleans (junk/wrong) |
| Raw rows → included → analytical | 294,901 → 197,627 → 172,339 (was 196,535 → 171,247 before the 14 Oct R5 correction) |

| City | Usable companies | With a standard one-time price for 3 bd / 2 ba / 1,700 sq ft | Note |
|---|---|---|---|
| Louisville | 4 harvested + R&R model + 6 published sources | 4 (+R&R first-clean) | Only city with hand-checked service areas |
| Indianapolis | 4 | 4 | |
| Columbus | 3 | 3 | |
| Nashville | 3 | 2 | Maid Cleaning Nashville sells only deep cleans |
| Kansas City, Omaha, Richmond | 2 each | 2 each | |
| Birmingham | 2 | 1 | Bear Bros standard service never captured |
| Knoxville, Memphis, Tulsa | 1 each | 1 each | |
| Oklahoma City, Grand Rapids | 1 each | 0 | Houses priced by sq ft only from 1,750 / no one-time option |
| Lexington, Cincinnati, Dayton, St. Louis, Milwaukee | 0 | 0 | No usable data |

No city has a random or complete sample. Peer companies were found by web search and kept only if they had a BookingKoala or Launch27 calculator, so they cannot be treated as representative of their market.

## 3. Issues found (full log: workbook "Issues" sheet)

### High severity

- **A1. Wrong profile prices in the 14 Oct market build.** `build_market.py` treated a blank bedroom count as "matches any bedroom" and took the cheapest row. Every Launch27 company whose services are named "One/Two/Three Bedroom Home" was priced as a 1-bedroom home. 44,278 market rows have blank bedrooms (18 companies). I rechecked all 2,196 values in `research/market/2026-10-14/profiles.csv`: **428 are wrong and 338 have no valid match**, 1,430 are unchanged (`data/old_profiles_recheck.csv`). Example: Super Cleaning, 3 bd / 2 ba / 1,800 sq ft, was shown as $245; the correct price is $255, the same as the 13 Oct live check. `city_index.csv`, `structure.csv` and `Market_Price_Matrix.xlsx` inherit the error, as did the figures I gave in chat on 13–14 Oct.
- **A2. Launch27 prices labelled "verified".** 38,910 rows are prices calculated from the booking platform's price feed, not observations of the live form. I re-derived the arithmetic for all 27,299 included Launch27 rows from the raw feeds (0 mismatches). That confirms the calculation matches the feed rules, **not** that customers see these prices. Only Super Cleaning has live spot checks (3, on 13 Oct).
- **A3. Red Feather (resolved 14 Oct by live check – see addendum).** 6,552 of 18,200 rows are unverified, all of them Move In/Out or Construction on recurring schedules. In the verified one-time rows, Move In/Out equals Deep Clean and Construction equals Basic for all 1,092 combinations, which suggests the service switch did not register. Bedroom and bathroom choices never change the price. Basic and Deep are kept; move-out is excluded until it can be checked on the live form. Separately, the 13 Oct workbook and README describe Red Feather as "lead-form only", which is wrong: it has an instant calculator.
- **A5/A6. Run problems.** St. Louis Clean Solutions ran for 7.7 h and saved nothing. Patriot Maids ran 52 min and saved nothing. Maid 2 Clean KY (Louisville) failed because its feed wasn't found (14 Oct: the detected host is an inactive account; the live host was captured in validation). Bear Bros stopped at the old 60,000-row cap, so its standard service was never captured. Rapids offers no one-time clean, and its deep/move rows were never verified.
- **A7. Template prices.** Deluxe Maid (Indianapolis) and Better Cleans (Milwaukee) have identical Launch27 price tables, so they are excluded.
- **A8. City assignment.** Fresh Space's booking host is `freshspacecleveland`. Bear Bros lists Huntsville, Birmingham and 30A. Best Clean KC serves the Kansas suburbs. Patriot Maids was returned for 6 cities. Seven usable peer companies are tied to their city only by the search result. No peer company's service area was checked by hand.

### Medium severity

- **A4. Scrub Lou entry-option duplicates (still present in the raw data).** 26,100 rows are 5,220 prices × 5 "how will the cleaner get inside" options, and the price never varies. They are collapsed to 5,220 in the analytical table. We Clean Nashville has the same issue (2,400 → 120).
- **A9. ZIP.** 10 of 19 BookingKoala forms had no ZIP field (default-location prices), and Launch27 ignores ZIP. The `zip` column in `market_matrix.csv` implies otherwise.
- **A10. Tax and fees.** There are unidentified surcharges over the pre-tax total: +3% (Bear Bros), +8% (Brightstone), about +5.75% (Lemon Maid; consistent with Ohio sales tax, unconfirmed). Rapids and We Clean Nashville show a single total, so their tax treatment is unknown. Launch27 feeds contain no tax.
- **A11. First vs recurring.** Only Maids in Apron, Her Cleaning Collective, Spruce Up and We Clean Nashville show first-visit and ongoing prices separately. Other BookingKoala forms show one per-visit figure. `city_index.csv` mixed the two bases.
- **A12.** 247 rows with a $0 total were included in `market_matrix.csv` as prices.
- **A13.** The 14 Oct build dropped R&R, Cleanoria, Stitch and the other 13 Oct Louisville sources.
- **A14.** Company names are page titles ("Homepage", "House Cleaning", "Apartment Cleaning Services").
- **A15.** Bed/bath selections don't change price at Red Feather, Spruce Up, Indy Cleans or Bear Bros (deep/move). Sq-ft-only pricing is plausible, but it needs a live check.
- **A19.** "No platform detected" was treated as "no online price". In 75 of the 244 site visits only the home page loaded.
- **A21.** Included tasks and checklists were not captured for any company.

### Low severity

- Placeholder or malformed options (Spruce Up, Her Cleaning, Best Clean KC, Novo "-Copy", Maids in Apron duplicate "1 - 2499" band, Brightstone "Deep Clean-Copy").
- Maid Complete's per-sq-ft counter was truncated (42 rows).
- `market_matrix.csv` is 70 MB, with 33,258 exact price duplicates.

## 4. What holds up

| Check | Result |
|---|---|
| Scrub Lou 14 Oct capture vs 13 Oct capture (independent runs) | 5,220 / 5,220 prices identical |
| Maids in Apron 14 Oct vs 13 Oct (tax-inclusive, first visit and recurring) | 4,312 / 4,312 first-visit and 3,234 / 3,234 recurring identical to the cent |
| Super Cleaning feed vs 13 Oct model | 10,800 / 10,800 identical; 13 Oct live checks ($255 / $270.30 / $202.73 / $314.03) agree |
| Launch27 arithmetic (all included rows) re-derived from raw feeds | 27,299 / 27,299 match |
| BookingKoala verification | 100% for standard services at most companies; unverified rows are concentrated in service/frequency pairs the forms don't offer |

## 5. Evidence tiers used (not equally verified)

1. **Live form observation:** BookingKoala Booking Summary, with selections confirmed. 18 usable companies. Scrub Lou and Maids in Apron are confirmed by two independent captures; the rest by one.
2. **Booking-platform feed calculation:** Launch27. Calculated, not observed, except Super Cleaning's 3 live checks.
3. **Reconstructed model:** Maids in Apron deep/move add-ons (live add-on checks, 13 Oct) and the Rocking Robins calculator formula (1 combination checked live).
4. **Published list or range:** Stitch, Cleanoria, Your Cleaning Krew, Busy Brooms, Hello Cleaners, LouBelle hourly. These are not quotes.
5. **Manual quote:** none collected. MaidPro, Merry Maids, The Maids, The Cleaning Authority and Maid in the Ville are contact-gated, so there are no prices for them.

## 6. Normalization and de-duplication rules applied

Rules R1–R10 (workbook "Rules" sheet; counts in `data/rule_counts.csv`):

| Rule | Description | Rows excluded (first reason) |
|---|---|---|
| R1 | Company exclusion | 9,434 |
| R2 | BookingKoala unverified | 55,678 |
| R3 | No price / $0 | 212 |
| R4 | Out of scope (Airbnb, post-construction, commercial, carpet, hourly, demo) | 20,941 |
| R5 | Red Feather construction only (move-out re-included 14 Oct after live check; construction is also R4) | 0 (was 1,092) |
| R6 | Launch27 non-size counters / truncated per-sq-ft counter | 42 |
| R7 | Placeholder options | 2,576 |
| R8 | Duplicates collapsed | 25,288 |
| R9 | Zero-bath homes | 5,892 |
| R10 | "-Copy" entries | 2,499 |

- Pre-tax price = "total before tax" where shown. For Maids in Apron = total ÷ 1.06, which matches the 13 Oct live checks. Otherwise the single displayed total is kept and flagged.
- Missing prices stay blank and are never set to $0.
- Duplicates are collapsed only when price and scope are identical and the differing field was shown not to affect price (checked group by group).
- Bedrooms are parsed from Launch27 service names. Bathrooms = full + 0.5 × half.

## 7. Documents that need correcting

| Document | Correction |
|---|---|
| `README.md` | Current-data counts (22,488 rows, 3 companies) are superseded. The ZIP / auto-label / 45-min-cap claims didn't apply to the 14 Oct run. Red Feather is not lead-form-only. Point to `research/analysis/2026-10-14`. |
| `research/2026-10-13/Louisville_Cleaning_Price_Matrix.xlsx` | Red Feather listed as lead-form only (Summary, Published Prices footnote). |
| `research/market/2026-10-14/*` | Do not use profiles, structure, city_index or the workbook (A1, A2, A3, A4, A12, A14). |
| `research/market/2026-10-14/market_matrix.csv` | `zip` and `verified` columns are misleading (A2, A9). |
| Chat summaries 13–14 Oct | City Index figures came from the buggy build. Corrected medians for the reference home: Louisville $247 (n=4), Indianapolis $207 (n=4), Columbus $204 (n=3), Nashville $216.50 (n=2). |

I have not edited these files. All corrections are in the new derived outputs.

## 8. Unresolved and needs verification (in priority order)

1. ~~Red Feather move-out prices and its sq-ft-only pricing~~ – resolved 14 Oct (live check: both genuine).
2. ~~Maid 2 Clean KY~~ – captured 14 Oct from its live host (smilesaremaid.launch27.com) and modelled; 9 live checks matched. Open: its terms say recurring discounts apply after the first visit, but the feed shows 0%.
3. Launch27 prices for peer-city companies: spot-check 2–3 combinations each on the live form (Louisville Launch27 sites now checked).
4. Peer service areas and identities (7 usable companies tied to their city by search only).
5. Tax/fee treatment where sites show one total or an unidentified surcharge.
6. ~~Included-task checklists for every Louisville competitor~~ – captured 14 Oct (research/checklists/2026-10-14); WebFetch-derived cells need re-reading before quoting.
7. Contact-gated Louisville companies: no prices without submitting contact details. Requests drafted, unsubmitted (research/quote-requests/2026-10-14); waiting on your home details.
8. Re-run failed and capped peer companies (St. Louis, Patriot Maids, Bear Bros standard, Rapids) with the current code if peer data is needed.
