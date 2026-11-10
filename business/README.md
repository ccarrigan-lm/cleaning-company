# Business: launch documents

Everything needed to run the cleaning company's launch offer. Each file here is the single current copy: edit it in place and let git keep the history. The market research these are built on is in `../research/`.

| File | What it is |
|---|---|
| `launch-plan.md` | What's done, what's next, and what only the owner can do |
| `price-list.md` | Customer-facing prices and what's included (website / quote wording) |
| `service-checklist.md` | The operational checklist: task-by-task cleaner instructions, operating rules, completion record |
| `policies.md` | Customer terms (draft for lawyer review) |
| `pricing/Pricing_Model.xlsx` | Where the prices come from: room minutes, rate, market check, margin check, quote calculator |
| `operations/Job_Tracker_TEMPLATE.xlsx` | Log of quotes, jobs and room times; shows real minutes vs estimates and suggests price updates |

## The offer in brief

- One thorough standard clean, priced per room, with six individually selectable add-ons. No deep-clean package.
- $150 minimum booking. First visit full price; 20% / 15% / 10% off for weekly / every 2 weeks / every 4 weeks from the second visit. 6% sales tax added at checkout.
- Fixed price: our estimating error never raises the bill.
- Visit record after every clean; missed work gets a free return or a proportionate refund.
- Prices sit at the Louisville median for a one-time standard clean (about 1% below on average across 10 home profiles; 10% below to 6% above).

## Changing a price

1. Change the input in `pricing/build_pricing_model.py` (room minutes, price per cleaner-minute, market position, an add-on price, the minimum or a discount) and rebuild:
   ```
   pip install -r ../requirements.txt
   python pricing/build_pricing_model.py
   ```
   Or try a change in the workbook's blue cells first; open it in Excel and everything recalculates.
2. Check the **Market check** sheet (position against competitors and margin).
3. Update `price-list.md`, the price mentions in `service-checklist.md` and `policies.md`, and the settings and prices in `operations/build_job_tracker.py`.
4. Change one thing at a time and give it a few weeks. Keep existing recurring customers on their price, or give notice.

## Tracking jobs

1. Copy `operations/Job_Tracker_TEMPLATE.xlsx` to `operations/Job_Tracker.xlsx`. That copy is git-ignored: **customer and job details, and all photos, stay out of Git.**
2. Log every quote (booked or not), every job, and each room's start and finish photo times.
3. The Summary sheet shows average real cleaner-minutes per room against the estimate, margin per job and the quote-to-booking rate. Once a room type has 5 timings it suggests a price.

## Launch defaults (chosen to get going; change any of them)

These were not individually decided by the owner. They were set on 10 Nov 2026 so the launch isn't blocked.

| Default | Value | Why |
|---|---|---|
| Recurring discounts | 20% / 15% / 10%, from the 2nd visit | The most common scheme in Louisville and peer cities; first visit stays full price because we have no deep-clean charge |
| Sales tax | 6% added at checkout | All five compared competitors charge it; Kentucky taxes residential cleaning. Confirm with an accountant. |
| Minimum booking | $150 | Covers setup, travel and a small job |
| Four tasks left out of the standard clean | Cabinet-front washing, grout scrubbing, full door/frame wipe, baseboard stain removal: custom quote only | Not timed or priced yet |
| Reach equipment | Extension duster and pole; no stools or ladders | Simplest and safest to start; revisit with the cleaners |
| Cancellation | Free up to 48 h; $50 inside 48 h; 50% if we can't get in | Common pattern; not checked against competitors |
| Payment | Card on file, charged after the clean | |
| Photos | Before and after, consent at booking, deleted after 90 days | Also gives room times |
| Cleaner cost in the margin check | $18/hour + 15% payroll load | Placeholder; replace with the real figure |

## Earlier drafts

`../research/our-offering/` keeps the dated checklist drafts (14 Oct draft, v2-v5) and the pilot timing sheet. They are superseded by this folder.
