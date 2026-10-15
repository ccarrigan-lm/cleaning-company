# Findings: Louisville residential cleaning prices (audited data, 14 Oct 2026)

All prices are pre-tax US$. Sources, evidence tiers and every number below are in `Louisville_Comparison_Validated.xlsx`. "Instant-price companies" means Scrub Lou, Maids in Apron, Super Cleaning, Red Feather and Maid 2 Clean; Rocking Robins (R&R) and the published lists are shown separately. **These prices come from competitors' online forms; none is a quote obtained for a specific home.**

**Updated 14 Oct (after live validation, `research/validation/2026-10-14/VALIDATION_REPORT.md`):** 40/40 live checks matched. Red Feather's move-out price (= its deep price) is real and is now included; Maid 2 Clean is added from its live booking feed (9 live checks); Super Cleaning now has 12 live checks. Competitor checklists are in `research/checklists/2026-10-14/`.

## Ready for business decisions

### 1. Louisville price levels (same homes, every source)

Standard clean, one-time:

| Home | Scrub Lou | Maids in Apron | Super Cleaning | Red Feather | Maid 2 Clean | Median | n | R&R first clean | Stitch (published) | Cleanoria (published range) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 bd / 1 ba / 750 | 169 | 165 | 170 | 175 | 142 | 169 | 5 | n/a | 150 | 125–145 |
| 2 bd / 2 ba / 1,200 | 219 | 190 | 230 | 205 | 174 | 205 | 5 | 210 | 180 | 155–175 |
| 3 bd / 2 ba / 1,600 | 249 | 219 | 255 | 245 | 200 | 245 | 5 | 420 | 220 | 205–255 |
| 3 bd / 2.5 ba / 2,200 | 279 | 224 | 295 | 285 | n/m | 282 | 4 | n/a | 220 | 225–275 |
| 4 bd / 2.5 ba / 2,500 | 309 | 294 | 325 | 325 | n/m | 317 | 4 | 480 | 250 | 225–275 |
| 4 bd / 3 ba / 3,000 | 339 | 304 | 360 | 375 | 246 | 339 | 5 | 540 | 290 | 245–295 |

n/m = no matching option (Maid 2 Clean's form takes whole bathrooms only). Maid 2 Clean is the low end of the instant-price group ($19–$93 below the other four). The other four are within $10–$71 of each other. R&R prices a *first-time* clean at $60 per labour hour, which puts it far above the rest. Published lists sit around or below the instant-price low end.

**Comparison basis (checked 14 Oct evening).**

All five columns price the same home:
- the same bedrooms and bathroom split (2.5 = 2 full + 1 half)
- a sq ft band that contains the profile
- the same service and visit type: the one-time standard clean, i.e. the first and only visit

Tax is treated differently:
- **Scrub Lou, Super Cleaning and Red Feather** add 6% KY sales tax at checkout, so they are shown before tax.
- **Maids in Apron's** total includes 6%, so it is divided by 1.06.
- **Maid 2 Clean** shows **no tax displayed; treatment unconfirmed**, so it is shown as displayed.

What this means for the median:
- **It doesn't depend on Maid 2 Clean's tax treatment.** Maid 2 Clean is the lowest price on every profile where it is priced, so only its presence matters.
- **$245 is a five-company pre-tax median.** It is $247 without Maid 2 Clean (n=4), and $259.70 on a customer-pays basis (the four with 6% added; Maid 2 Clean as displayed).
- **The 4 bd / 3 ba / 3,000 sq ft median is $339 to $344.** Two of Maids in Apron's sq ft bands include 3,000 sq ft ($304 or $344).
- Every profile and case, with and without Maid 2 Clean, is on the workbook's **Five-Company Basis** sheet (`data/louisville_five_company_basis.csv`).

**Sampled live verification vs untested combinations.**
- **Scrub Lou, Maids in Apron and Red Feather:** every cell is a live form observation from the 13–14 Oct harvest. 22 Red Feather combinations were re-checked live on 14 Oct.
- **Super Cleaning and Maid 2 Clean:** cells are calculated from the price table the booking form downloads. Only 12 (Super) and 9 (Maid 2 Clean) combinations were checked on the live form. All matched, but the other combinations are untested.
- **Automated validation (15 Oct):** All 38 planned price checks passed across two automated runs on 15 Oct 2026 (6 in run 1, the other 32 in run 2); combinations outside that sample remain untested. The 38 checks cover small, typical and larger homes × one-time, biweekly and deep at Super Cleaning and Maid 2 Clean, plus 20 Red Feather bedroom, bathroom, sq ft and service checks. Every other cell is still untested. See `research/validation/2026-10-15-automated-run2/`.

3 bd / 2 ba / 1,600 sq ft by service and frequency:

| | Scrub Lou | Maids in Apron | Super Cleaning | Red Feather | Maid 2 Clean |
|---|---|---|---|---|---|
| Every 2 weeks, price shown | 212 | 219 first visit, then 204 | 191 (every visit incl. first; live-checked) | 208 | 200 (no discount) |
| Weekly, price shown | 199 | 219 first, then 199 | 166 | 196 | 200 (no discount) |
| Deep clean | 429 | 404 (model from live add-on checks) | 395 | 275 (live-confirmed) | 250 |
| Move-in / move-out | 529 | 429 | 410 | 275 (= deep; live-confirmed; one-time only) | 299 |

Cleanoria publishes $245–$295 for a deep clean of this home and R&R charges $480.

### 2. What changes the price in Louisville (reference home 3 bd / 2 ba / 1,700 sq ft)

| | Scrub Lou | Maids in Apron | Super Cleaning | Red Feather | Maid 2 Clean |
|---|---|---|---|---|---|
| +1 bedroom | +$10 | +$30 | +$10 | $0 (live-confirmed) | +$14 |
| +1 full bath | +$20 | +$15 | +$35 | $0 (live-confirmed) | +$10 |
| +1,000 sq ft | +$40 | +$40 | +$40 | +$110 | +$15 |
| Weekly / 2-wk / 4-wk discount | 20 / 15 / 0% on every visit | $20 / $15 / $10 off later visits only | 35 / 25 / 10% on every visit | 20 / 15 / 10% on the price shown | 0% in the feed (terms say discounts start after the first visit – unresolved) |
| Deep ÷ standard | 1.72× | 1.84× | 1.55× | 1.12× | 1.25× (flat +$50) |
| Move-out ÷ standard | 2.12× | 1.96× | 1.61× | 1.12× | 1.50× (flat +$99) |

Add-ons: inside oven $45 / $45 / $65 / not published / $25; inside fridge $45 / $45 / $65 / not published / $25 (Red Feather's "+$50–$100" turned out to be a US-average table, not its own price); interior windows $4–$8 each ($60 flat at Maid 2 Clean). Scrub Lou credits $10 per excluded bedroom, full bath, kitchen or living room ($5 per half bath); Maid 2 Clean credits $10 per room not cleaned.

### 3. Structure patterns elsewhere (examples, not market levels)

These figures come from 23 companies in 12 peer cities, found by search and kept only if they had an online calculator. City samples are 1–4 companies, so treat them as **pricing-design examples**, not market prices, and don't convert them to Louisville prices.

| Metric (reference home) | Median | Range | n |
|---|---|---|---|
| +1 bedroom | $10 | $0–$40 | 18 |
| +1 full bath | $20 | $0–$40 | 19 |
| +half bath | $10 | $0–$20 | 14 |
| +1,000 sq ft | $40 | $0–$103 | 17 |
| Discount on price shown, weekly / 2-wk / 4-wk | 20% / 15% / 10% | 0–25% | 16–17 |
| Deep ÷ standard | 1.43× | 1.14–2.34× | 14 |
| Move-out ÷ standard | 1.62× | 1.14–2.64× | 13 |

Across all 27 usable companies, pricing inputs break down as:
- bedrooms + bathrooms + sq ft: 14
- sq ft only: 7 (bed/bath asked but not priced at 4 of them)
- bedrooms + bathrooms only: 5
- bathrooms + sq ft: 1

"20 / 15 / 10% off" for weekly / every 2 weeks / every 4 weeks is the most common frequency scheme.

## What the evidence says about a transparent room- and service-based offering

**Findings (supported by the data)**
- No Louisville instant-price competitor prices room by room. All five sell a whole-home package priced from size inputs plus add-ons. Room-level prices appear only as Scrub Lou's exclusion credits and Maids in Apron's "extra kitchen" ($90) and "finished basement" ($120) add-ons. One peer, Spruced Up Cleans (Columbus, city evidence = search only), publishes a full room-count formula: $40 base + $15/bedroom + $20/full bath + $10/half bath + $20/kitchen + $10/utility room + $16/other room.
- Bedrooms and bathrooms move Louisville prices by only $0–$35 each. Sq ft bands and the base price carry most of the price.
- A simple whole-home size formula tracked the Louisville four-company median within ±$11 on the 10 home profiles (13–14 Oct fit, before Maid 2 Clean was added). Bed, bath and sq ft rise together across these profiles, so the individual coefficients don't mean much.
- Competitors are not transparent about everything. Only Maids in Apron and Maid 2 Clean show the first-visit and recurring price separately. Tax: 6% at Scrub Lou, Red Feather and Super Cleaning (added at checkout) and Maids in Apron (included in its total); Maid 2 Clean: no tax displayed; treatment unconfirmed. Included-task checklists were captured on 14 Oct (`research/checklists/2026-10-14/CHECKLIST_FINDINGS.md`): every company includes the same core; inside fridge/oven/windows are paid extras at 4 of the 5 priced companies (Red Feather publishes none); and "deep clean" means a different task list at each company. A first draft of our own standard checklist is in `research/our-offering/2026-10-14/STANDARD_CLEAN_CHECKLIST_DRAFT.md`.

**Hypotheses (not tested by this data)**
- Customers prefer seeing room-by-room line items to a size-band price.
- A room-based price list can land inside the Louisville range for typical 2–4 bedroom homes.
- Publishing a task checklist and showing first-visit and ongoing prices up front is a meaningful differentiator.
- A room-based model prices unusual homes more fairly than sq ft bands, for example many small rooms, or large open plans.

## Still needs verification

- ~~Red Feather move-out and sq-ft-only pricing~~ — **resolved 14 Oct** by live validation (both genuine).
- **Launch27-calculated prices:** sampled live for Super Cleaning (12 checks) and Maid 2 Clean (9 checks), all matched; all other combinations are calculated, not observed; peer-city Launch27 feeds are unchecked. Tax treatment is unknown where a site shows one total (incl. Maid 2 Clean).
- **Beyond the 38-check sample:** combinations outside that sample remain untested. Network-audit limitation: request bodies were not stored, so the 127 non-GET requests' contents cannot be audited - only their methods, URLs, types and sizes.
- **Maid 2 Clean recurring discount:** the feed and live form show 0%, but its terms say recurring discounts apply after the first visit; its homepage widget shows a different (higher, discounted) formula.
- **Peer company service areas:** none reviewed by hand. One misassigned company and two template companies were found and excluded.
- **Included tasks:** captured verbatim for 17 companies (all re-read in the browser 14 Oct evening). Hello Cleaners is excluded from Louisville conclusions (national platform; no Louisville operator named). Stitch's Louisville identity is verified (KY Secretary of State: active Jefferson County LLC). These are published claims, not observed cleans.
- **Contact-gated competitors:** MaidPro, Merry Maids, The Maids, The Cleaning Authority, Maid in the Ville have no prices online; requests are drafted and unsubmitted (`research/quote-requests/2026-10-14/QUOTE_REQUESTS.md`) pending your home details.
- **Prices at other Louisville ZIPs:** only one ZIP (40217) was used, so pricing by distance or neighbourhood was not tested.

## Operational inputs needed before setting our prices

The data gives the market range. None of the following is in it, and I have not assumed any of them:

1. **Cleaner compensation:** hourly rate or per-job pay, payroll taxes, workers' comp, benefits or bonuses, paid travel time. Competitors' customer-facing hourly prices are $60–$65 per cleaner-hour (Super Cleaning and several Launch27 sites), $60 per labour hour (R&R) and $40 per technician-hour (LouBelle). These are prices, not wages.
2. **Time per task:** minutes per bedroom, full bath, half bath, kitchen and living area. Also the extra time for a deep clean, a move-out and a first visit, and the effect of condition (pets, build-up). These numbers are needed to turn room counts into labour.
3. **Team model:** solo or 2-person crews, and the minimum job length.
4. **Supplies and equipment:** cost per visit and per room type.
5. **Travel:** service radius or zones, average drive time and mileage between jobs, and whether to charge by zone.
6. **Overhead:** insurance and bonding, booking software, card processing (%), marketing / cost per new customer, admin, owner pay.
7. **Tax:** whether and how KY sales tax applies to your services. Competitors add 6%; confirm with an accountant.
8. **Policies with cost:** re-clean guarantee, cancellations, minimum charge, recurring-customer retention.
9. **Target margin**, and where in the Louisville range you want to sit.

With items 1–6, each room/service price can be built as labour time × loaded cost + supplies + travel + overhead share, then checked against the Louisville comparison above.
