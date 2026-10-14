# Louisville service checklists: what competitors include (captured 14 Oct 2026; re-verified the same evening)

**Scope.** I read the published checklists, service pages and terms for 17 companies:
- the 5 instant-price companies
- R&R
- 6 published-price companies
- the 5 contact-gated companies

The grid has 52 tasks × 17 companies × standard / deep / move, with supporting text and URLs:
- `task_matrix_long.csv` and `task_matrix_wide.csv`: the grid
- `raw/`: raw text
- `task_summary.csv`: counts
- `python3 build_matrix.py`: rebuilds everything

**Which companies count for Louisville conclusions.** The conclusions use 16 companies:
- **Hello Cleaners is excluded.** It is a national booking platform ("Vetted · Insured · nationwide", with a 307 area-code phone). Its Louisville page is templated census text, and no Louisville operator is named. Its cells stay in the grid for reference.
- **Stitch Cleaning is included.** Its identity was verified with the Kentucky Secretary of State on 14 Oct: an active Kentucky LLC, primary county Jefferson, filed July 2024, whose principal office in Fairdale, KY 40118 matches its website. The 407 phone number alone doesn't contradict that.

**How each cell is coded.**

| Code | Meaning |
|---|---|
| Inc | Explicitly included |
| Excl | Explicitly excluded |
| Paid | Paid extra |
| Cond | Conditional ("upon request", "as needed", "if provided") |
| – | Not stated |

Silence is always coded as not stated. A task one company calls "deep" is never assumed to be in another company's deep clean.

**How much to trust it.** Every company's pages were read in the built-in browser and saved verbatim in `raw/`. That includes the five companies first read with a summarising tool (Maids in Apron, Super Cleaning, R&R, Stitch, Hello Cleaners), plus Cleanoria and Red Feather's move page, all re-read on the evening of 14 Oct.

**What the re-read changed.** 55 cells changed, listed in `corrections_vs_first_version.csv`. The main corrections:
- **Red Feather add-on prices withdrawn.** Its "+$50–$100" add-on price was a table of US-wide average prices on its move page, not Red Feather's own prices. Red Feather publishes no add-on prices, so inside fridge, oven and windows are now "not stated" for its standard clean.
- **Maids in Apron's terms add a ladder ban, a mold and hoarding refusal, and charges for extra time and de-cluttering.** Its terms also say deep cleaning "is billed hourly" as an add-on to a standard clean. Its booking form showed a flat add-on price; that conflict is recorded, not resolved.
- **Super Cleaning:** "Remove Fingerprints/Smudges" doesn't name light switches, so switches are now "not stated".
- **R&R:**
  - Ceiling fans and fixtures are conditional ("within 2-step ladder reach"; vaulted and wobbly ones skipped).
  - Toilets are not named on any R&R list.
  - Its FAQ says it uses the client's vacuum and toilet brush, and also says its teams arrive fully equipped. Both statements are on the page.
- **Stitch:** the regular-clean list is four generic lines, and regular plans start with a deep clean after a home walkthrough. Its two pages disagree on recurring discounts: one says 25/20/15% off, the other says "up to 15%" plus 10% off the first booking.
- **Hello Cleaners:** grout is "treated" in its standard clean, while its own FAQ calls detailed grout a deep task, so it is coded conditional.

**Companies with little or no task list.** Most of their cells are "not stated":
- Busy Brooms (no task list)
- Cleanoria (no task list; extras listed without prices)
- Maid in the Ville (a few lines only)
- LouBelle (deluxe items only; full checklist on request)

## What the evidence shows

### 1. A common core

All 5 instant-price companies include these in their standard clean, as do most companies that publish a standard list:
- counters and backsplash
- kitchen sink
- stovetop
- appliance exteriors
- toilet, tub/shower, bathroom sink, mirrors
- dusting reachable surfaces
- vacuuming and mopping
- emptying trash

Close behind (4 of 5 priced): window sills, ceiling fans, light fixtures.

Fewer (3 of 5 priced): inside microwave, making beds, cobwebs, stairs.

### 2. These are sold as extras

At 4 of the 5 priced companies, inside fridge, inside oven and interior windows are paid extras. Red Feather publishes no add-on prices.

| Task | Price |
|---|---|
| Inside fridge | $25–$65 |
| Inside oven | $25–$65 |
| Interior windows | $4–$8 per window, or a $60 flat fee (Maid 2 Clean) |

Other items paid at at least one company:

| Task | Price |
|---|---|
| Inside cabinets | $5 per unit, or $20 |
| Laundry | $20–$65 |
| Basement | $50–$120 |
| Pets | $10–$20 |
| Wet-wipe blinds | $5 per set |
| Wet-wipe baseboards | $20 per floor |
| Spot-clean walls | $25 |
| Organizing | $60/hour, or $375 for a house |
| Extra time | $32.50 per 30 minutes |
| Linens | $10 |
| Couch vacuuming | $10–$15 |

### 3. Many tasks change tier from company to company

- **Inside microwave.**
  - Standard at Scrub Lou, Red Feather, Maids in Apron, Your Cleaning Krew, MaidPro, The Maids and The Cleaning Authority ("wiped out").
  - Deep or move only at R&R.
  - Not specified at Super Cleaning and Maid 2 Clean ("Microwave").
- **Range hood.**
  - Excluded from standard at Scrub Lou.
  - Deep at Red Feather and Your Cleaning Krew.
  - Outside cleaned in The Cleaning Authority's normal clean.
- **Baseboards.**
  - Dusted in standard at Super Cleaning, Red Feather, MaidPro and R&R.
  - "Scrub Baseboards" in Maids in Apron's single list.
  - Hand-wiped only in deep at Scrub Lou, Super Cleaning, Red Feather, R&R, Your Cleaning Krew and The Cleaning Authority.
  - A $20-per-floor extra at Maid 2 Clean.
- **Blinds.**
  - Dusted in standard at Super Cleaning, The Cleaning Authority, Maids in Apron, and lightly at Red Feather.
  - "Upon request" at MaidPro.
  - Paid at Maid 2 Clean ($5 per set) and R&R ($20 each, from its booking calculator).
  - Scrub Lou refuses fragile blinds.
- **Doors, frames and switch plates.**
  - Usually deep or move only (Scrub Lou, R&R, Your Cleaning Krew, Merry Maids, Red Feather move).
  - Standard at MaidPro and Maids in Apron.
  - "As needed" at Maid 2 Clean.
- **Cabinet fronts.**
  - Spot-cleaned or "as needed" in standard at Scrub Lou, Super Cleaning and Maid 2 Clean.
  - Fully wiped in deep.
- **Grout scrubbing.** Deep or move only wherever stated (Scrub Lou, Red Feather move, Your Cleaning Krew, The Cleaning Authority rotation). Maids in Apron disclaims grout expertise.
- **Inside cabinets, inside closets and appliance interiors.** Built into move-out at nearly every company that lists move tasks. In standard they are an extra.

### 4. What "deep clean" means differs by company

Each company's deep clean covers different tasks:
- **Scrub Lou:** doors, hood, sills, cabinet exteriors, baseboards, grout, inside the linen closet.
- **Super Cleaning:** hand-washed baseboards, wood trim and cabinet exteriors; full soap-scum removal; kitchen grease.
- **Red Feather:** blinds, baseboards, fans, hood degreasing, interior appliances.
- **R&R:** everything hand-washed within 2-step reach, including cabinet fronts, doors and switch plates, inside microwave, and a double-scrubbed tub.
- **Your Cleaning Krew:** 65 points, including inside the fridge and oven, blinds, walls and grout.
- **Maid 2 Clean:** a $50 add-on with no separate task list (for homes not cleaned in 30+ days).
- **Maids in Apron:** an add-on. Its terms say it is billed hourly.
- **Stitch:** whole-home detail including windows, blinds and tracks, high shelves and under furniture.
- **The Cleaning Authority:** no single deep visit. It rotates detail cleaning through four zones, and its first two recurring visits are deep cleans.

Comparing deep-clean prices without this table compares different products.

### 5. Exclusions are published by only a few companies

**Explicit refusals.** Mostly published by Scrub Lou, Super Cleaning, Maid 2 Clean, R&R, Maids in Apron and Stitch:
- moving heavy furniture (4 companies)
- ladders and heights (5; Maids in Apron allows no stools at all)
- biohazards, mold and hoarding (4)
- hauling away trash (3)
- wet-wiping light bulbs (2)
- exterior windows (1)
- dishes (R&R)

**Exceeding the estimate.** Scrub Lou, Maids in Apron, Maid 2 Clean, R&R and Super Cleaning say price or time can change when a home takes longer than estimated. Super Cleaning and Stitch publish a paid option for it.

### 6. Conditions that matter for scope wording

- Beds and linens: "if provided" or "if left out".
- Ceiling fans and fixtures: "height restrictions", "reasonable height", or "within 2-step ladder reach".
- Under furniture: only "if accessible".
- Move-out cleans assume an empty home (Maid 2 Clean, Red Feather, Super Cleaning's "inside empty cabinets", R&R's "vacant homes").
- An initial deep clean may be required first at Your Cleaning Krew, LouBelle, Stitch and The Cleaning Authority. Super Cleaning recommends one if the home hasn't been professionally cleaned in the last 3 months.
- Maid 2 Clean's terms say recurring discounts start after the first visit. Its live booking feed shows 0% (see validation).

## Recommendations for our offering

These are proposals. The competitor data shows market norms, not how long each task takes. The first draft of our checklist is in `research/our-offering/2026-10-14/STANDARD_CLEAN_CHECKLIST_DRAFT.md`.

**Include in the standard flat price.** 5 of 5 priced competitors include:
- counters and backsplash
- sink and stovetop
- appliance exteriors
- toilet, tub/shower, bathroom sink and fixtures, mirrors
- dusting reachable surfaces
- vacuum and mop
- empty trash

4 of 5 include:
- sills
- light fixtures
- ceiling fans within stool reach

**Probably include, but confirm with a time trial.** 3 of 5 include:
- inside microwave
- making beds
- cobwebs
- stairs
- baseboards dusted

**Price as separate per-unit add-ons, each with its own time estimate:**
- inside fridge
- inside oven
- inside cabinets
- interior windows
- wet-wipe blinds
- hand-wipe baseboards
- spot-clean walls
- changing linens
- laundry
- dishes
- basement
- garage
- organizing
- couch vacuuming
- pet-hair surcharge
- extra time beyond the estimate

**Define deep and move-out as named task lists, not multipliers.** Competitors' deep-to-standard price ratios run from 1.12× to 1.84×.

**Publish exclusions** and a condition clause, as the clearest competitors do.

## Limitations

- National franchises (Merry Maids, The Maids, The Cleaning Authority, MaidPro) mostly publish national pages; several say services "may vary by location".
- Two pages of the same company sometimes disagree, and both are recorded:
  - Stitch's two discount schedules.
  - Maids in Apron's hourly vs flat-rate deep clean.
  - Hello Cleaners on grout.
  - R&R on supplies.
- Your Cleaning Krew links to an instant quote at booking.yourcleaningkrew.com. It was not captured, so its prices are still the published hourly rates.
- These are published claims. None was observed in a real clean.
