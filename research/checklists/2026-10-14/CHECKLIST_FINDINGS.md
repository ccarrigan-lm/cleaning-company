# Louisville service checklists: what competitors include (captured 14 Oct 2026)

**Scope.** I read the published checklists, service pages and terms for 17 Louisville companies: the 5 instant-price companies, R&R, 6 published-price companies, and the 5 contact-gated companies. The full grid is in `task_matrix_long.csv` and `task_matrix_wide.csv`: 52 tasks × 17 companies × standard / deep / move, with supporting text and URLs. Raw text is in `raw/`. Counts are in `task_summary.csv`. Rebuild with `python3 build_matrix.py`.

**How each cell is coded.**

| Code | Meaning |
|---|---|
| Inc | Explicitly included |
| Excl | Explicitly excluded |
| Paid | Paid extra |
| Cond | Conditional ("upon request", "as needed", "if provided") |
| – | Not stated |

Silence is always coded as not stated. A task one company calls "deep" is never assumed to be in another company's deep clean.

**How much to trust it.** Pages read in the built-in browser were captured verbatim. Pages read with the WebFetch tool (Maids in Apron, Super Cleaning, R&R, Stitch, Hello Cleaners, Cleanoria, Red Feather move page) are model-extracted summaries: re-open the URL before quoting them. Three companies publish no usable task list, so nearly all their cells are "not stated":
- Busy Brooms
- Cleanoria
- Maid in the Ville (beyond a few lines)

## What the evidence shows

### 1. A common core

Every company that publishes a standard list includes the same core: counters, kitchen sink, appliance exteriors, toilet, tub/shower, bathroom sink, mirrors, dusting reachable surfaces, vacuuming, mopping, and emptying trash. All 5 instant-price companies include every item. Stovetop, window sills, light fixtures and stairs are close behind.

### 2. These are sold as extras

At all five priced companies, inside fridge, inside oven and interior windows are extras:

| Task | Price |
|---|---|
| Inside fridge | $25–$65 |
| Inside oven | $25–$65 |
| Interior windows | $4–$8 per window, or a $60 flat fee (Maid 2 Clean) |

Other items that are paid at at least one company:

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

- **Inside microwave.** Standard at Scrub Lou, Red Feather, Maids in Apron, Your Cleaning Krew, MaidPro and The Maids. Deep-only at R&R. Not specified at Super Cleaning and Maid 2 Clean.
- **Range hood.** Excluded from standard at Scrub Lou. Deep at Red Feather and Your Cleaning Krew. Normal clean at The Cleaning Authority.
- **Baseboards.**
  - Dusted in standard at Super Cleaning, Red Feather and MaidPro.
  - Hand-wiped only in deep at Scrub Lou, Super Cleaning, R&R, Your Cleaning Krew and The Cleaning Authority.
  - A $20-per-floor extra at Maid 2 Clean.
  - Wiped in the one list Maids in Apron publishes.
- **Blinds.**
  - Dusted in standard at Super Cleaning and The Cleaning Authority, and lightly at Red Feather.
  - "Upon request" at MaidPro.
  - A paid extra at R&R ($20 each) and Maid 2 Clean ($5 per set).
  - Scrub Lou refuses fragile blinds.
- **Doors, frames and switch plates.** Usually deep-only (Scrub Lou, R&R, Your Cleaning Krew, Merry Maids). Standard at MaidPro and Maids in Apron. "As needed" at Maid 2 Clean.
- **Cabinet fronts.** Spot-cleaned or "as needed" in standard at Scrub Lou, Super Cleaning and Maid 2 Clean. Fully wiped in deep.
- **Grout scrubbing.** Deep or move only, except Hello Cleaners, which lists grout in its standard clean.
- **Inside cabinets, inside closets, and appliance interiors.** Built into move-out at nearly every company that lists move tasks. In standard they are an extra.

### 4. What "deep clean" means differs by company

Each company's deep clean covers different tasks:

- **Scrub Lou:** doors, hood, sills, cabinet exteriors, baseboards, grout, inside the linen closet.
- **Super Cleaning:** hand-washed baseboards and trim, cabinet exteriors, full soap-scum removal, kitchen grease.
- **Red Feather:** blinds, baseboards, fans and hood, plus interior appliances.
- **Your Cleaning Krew:** 65 points, including inside the fridge and oven, blinds, walls and grout.
- **Maid 2 Clean:** a $50 add-on with no separate task list ("extra time" for homes not cleaned in 30+ days).
- **The Cleaning Authority:** no single deep visit. It rotates detail cleaning through four zones, and its first two recurring visits are deep cleans.

Comparing deep-clean prices without this table compares different products.

### 5. Exclusions are published by only a few companies

**Explicit refusals.** Scrub Lou, Super Cleaning, Maid 2 Clean and R&R publish most of the exclusions:
- moving heavy furniture (4 companies)
- tall ladders and heights (4)
- biohazards (3)
- hauling away trash (3)
- wet-wiping light bulbs (2)
- exterior windows (1)
- dishes (R&R)

**Exceeding the estimate.** Scrub Lou, Maid 2 Clean and Super Cleaning say price or time can change when a home takes longer than estimated.

### 6. Conditions that matter for scope wording

- Beds and linens: "if provided" or "if left out".
- Ceiling fans: "height restrictions" or "reasonable height".
- Under furniture: only "if accessible".
- Move-out cleans assume an empty home (Maid 2 Clean, Red Feather, Super Cleaning: "inside empty cabinets").
- Your Cleaning Krew and LouBelle may require an initial deep clean first.
- Maid 2 Clean's terms say recurring discounts start after the first visit. Its live booking feed shows 0% discounts (see validation).

## Recommendations for our offering

Treat these as proposals to price with your own time studies. The competitor data shows market norms, not how long each task takes.

**Include in the standard flat price**, because all 5 priced competitors include them and customers will expect them:
- kitchen counters and backsplash
- sink and stovetop
- appliance exteriors
- inside microwave
- toilet, tub/shower, bathroom sink and fixtures, mirrors
- dust reachable surfaces, sills and light fixtures
- ceiling fans within reach of a step stool
- baseboards dusted
- vacuum and mop all floors and stairs
- empty trash and tidy
- make beds (change linens if fresh linens are left out)

**Price as separate per-unit add-ons, each with its own time estimate.** These are the tasks competitors sell separately and whose time varies most:
- inside fridge
- inside oven
- inside cabinets (per cabinet bank or per kitchen)
- interior windows (per window, with or without tracks)
- wet-wipe blinds (per set)
- hand-wipe baseboards (per floor)
- spot-clean walls
- laundry (per load)
- dishes
- basement
- garage
- organizing (per hour)
- couch or upholstery vacuuming
- pet-hair surcharge
- extra time when condition exceeds the estimate (per 30 minutes)

**Define deep and move-out as named task lists, not multipliers.** For deep, add to standard:
- hand-wiped baseboards
- doors and frames, switch plates
- cabinet fronts
- hood degreasing
- grout scrub
- blinds

For move-out, add to deep:
- inside cabinets and drawers, inside closets
- inside fridge, oven and microwave
- vents

Each needs its own time estimate, because competitors' deep-to-standard price ratios run from 1.12× to 1.84×.

**Publish exclusions**, as the clearest competitors do:
- moving heavy furniture
- ladders above a stated step height
- biohazards, pet waste and mold
- hauling away trash
- exterior windows
- wet-wiping light bulbs

Also publish a condition clause: if the home takes longer than estimated, offer extra time at a published rate or let the customer choose priorities.

**Still to decide:**
- Whether inside microwave and cabinet fronts are standard. They are standard at most competitors, but conditional at three.
- Whether a first visit must be a deep clean, as at Your Cleaning Krew, LouBelle and The Cleaning Authority.

## Limitations

- Pages read with WebFetch are summaries, so any quote taken from them needs re-checking on the live page. Red Feather's move-page details are collapsed on the live page and come from WebFetch.
- National franchises (Merry Maids, The Maids, The Cleaning Authority, MaidPro) mostly publish national pages. Several say services "may vary by location".
- Stitch Cleaning's pricing page shows a 407 (Florida) phone number. Its Louisville identity should be checked before relying on it.
- Hello Cleaners is a national operator with templated city pages.
- Your Cleaning Krew links to an instant quote at booking.yourcleaningkrew.com. It was not captured, so its prices are still the published hourly rates.
