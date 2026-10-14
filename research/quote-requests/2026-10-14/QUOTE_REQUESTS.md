# Manual quote requests: five contact-gated Louisville companies (prepared 14 Oct 2026, NOT submitted)

Status: **all five are drafted and unsubmitted.** Nothing was typed into any contact, address or phone field. The only entry was ZIP 40217 in The Cleaning Authority's office lookup, which is not a quote request. Field lists and consent wording are copied verbatim in `research/checklists/2026-10-14/raw/`.

## 1. Instant pricing check (done 14 Oct)

None of the five shows a price before you submit contact details:

| Company | Quote route | Price shown before contact? | Required before any price | Free-text box? | Marketing / SMS opt-in |
|---|---|---|---|---|---|
| MaidPro – Greater Louisville | https://www.maidpro.com/greater-louisville/estimate | No; office calls or emails back | first name, last name, ZIP, email, **phone** | No | "I Agree" box = consent to marketing calls and texts. Unchecked by default, "not required". **Leave unchecked.** |
| Merry Maids – Louisville (1807 Cargo Ct, 40299) | https://merrymaids.com/home-cleaning-quote | No; step 1 is the street address | **street address** (later steps not viewed) | Not seen | Not seen at step 1. Check each later step. |
| The Maids – Southern Louisville | https://www.maids.com/estimates/ | No; "Your Pricing" comes after contact step | first/last name, email, **phone**, **street address**, ZIP, sq ft, bedrooms (whole), bathrooms (whole), clean level, frequency **or** one-time service type | No | Two optional boxes, "promotional emails" and "promotional texts". Both unchecked. **Leave unchecked.** |
| The Cleaning Authority – Louisville | https://estimate.thecleaningauthority.com/ → ZIP → step 1 of 3 | No; price on step 2 (13 Oct note) | first/last name, phone, email, address, city/state/ZIP, how heard, Recurring vs One-Time | No | Optional "recurring text messages ... offers and promotions" box, unchecked. **Leave unchecked.** |
| Maid in the Ville | https://www.maidintheville.com/request-an-estimate (or email maidintheville@gmail.com) | No | first/last name, email, phone, "How often do you need cleaning?" (free text), how heard | Only the "how often" line | None on the form |

Practical consequences:
- **Free-text questions.** MaidPro, The Maids and The Cleaning Authority have no message box. The questions below have to go in a short follow-up email once they reply, or be asked on their call.
- **One-time vs recurring.** The Maids and The Cleaning Authority make you choose one per submission. Choose **Recurring – Every Other Week**, because recurring sign-up exposes first-visit charges (The Cleaning Authority says its first two recurring visits are deep cleans). Ask the one-time price in the follow-up.
- **Maid in the Ville.** Email is the cleaner route: the whole request fits in one message, and nothing goes through a form.
- **Bathroom counts.** The Maids only accepts whole numbers. Enter full baths there and mention half baths in the follow-up.

## 2. Home profile

**No confirmed profile of your actual home exists in the project or in my notes.** The ten profiles in `analyze.py` (P1–P10) and `src/scenarios/profiles.ts` are synthetic market-comparison homes, and I have not used any of them here.

One consistent profile is needed for all five requests. **Please send these together:**

1. **Street address and ZIP** (Merry Maids, The Maids and The Cleaning Authority require it).
2. **Bedrooms**, plus whether any is used as an office or den.
3. **Full bathrooms** and **half bathrooms**.
4. **Finished square footage** (approximate is fine).
5. **Stories / levels**, and **basement**: none, unfinished, or finished, plus whether a finished basement should be cleaned.
6. **Pets**: none, or type and number.
7. **Current condition / last professional clean** (The Maids asks: Very Clean / Somewhat Clean / Average / Somewhat Dirty / Mostly Dirty).
8. **Main flooring**: mostly carpet, hard floors, or mixed.
9. **Name** to put on the requests.
10. **Phone number.** It is required by MaidPro and The Maids, and asked by The Cleaning Authority and Maid in the Ville. Tell me which number to use, or whether to skip companies that insist on one.
11. **Anything to leave out or include** (e.g. no laundry, include inside fridge), or confirm "standard clean only, no add-ons".

Email for all requests: **researching4clean@gmail.com**.

## 3. The request (same wording for every company)

Use it as the email body for Maid in the Ville, and as the follow-up email or call script for the other four. Placeholders are in [brackets].

> Hello,
>
> I'd like pricing for a **standard (not deep) house cleaning** at [street address, ZIP]. The home has [N] bedrooms, [N] full and [N] half bathrooms, about [N] sq ft on [N] level(s), [basement: none / unfinished / finished – include or exclude], [pets]. It was last professionally cleaned [when], and the floors are mostly [carpet / hard floors / mixed].
>
> Could you tell me:
> 1. The price of a **one-time standard clean**.
> 2. Whether the **first visit** is charged differently (for example, a required initial or deep clean) and, if so, how much.
> 3. The **price per visit for every-two-weeks service** after the first visit.
> 4. Which **tasks are included** in the standard clean (a checklist is perfect), and which are extra.
> 5. Any **mandatory fees**, such as trip, supply, booking, deposit or card fees, and whether **sales tax** is added.
>
> Email is the best way to reach me: researching4clean@gmail.com. Please don't add me to marketing or text lists.
>
> Thank you,
> [Name]

Per-company form entries, once the profile is confirmed:

| Field | MaidPro | Merry Maids | The Maids | The Cleaning Authority | Maid in the Ville |
|---|---|---|---|---|---|
| Service | Frequency: Bi-Weekly | (later steps) | Recurring → Every Other Week | Recurring | "How often": "Every two weeks; also want one-time price – details by email" |
| Beds / baths | free text: [N] / "[N] full, [N] half" | (later steps) | dropdowns (full baths) | not on step 1 | in email |
| Sq ft / condition | — (follow-up) | (later steps) | sq ft; clean level | — | in email |
| Marketing boxes | leave "I Agree" **unchecked** | check each step | leave both **unchecked** | leave SMS box **unchecked** | none |
| Promo code | none | — | — | — | — |
| How heard | — | — | — | "Online" | "Google" |

## 4. What to record when replies arrive

Save each reply in this folder as `<company>_<date>.md`. Record:
- the quoted one-time price, first-visit price and biweekly price
- whether the first visit is a required deep or initial clean
- the included-task list
- mandatory fees, tax and minimums
- whether the quote is an estimate (in-home or phone walkthrough) or firm
- any promotion, kept separate from the normal price (e.g. MaidPro's $25 off the 1st, 3rd and 5th cleans, and code 75OFF from 13 Oct)

Evidence tier: **manual quote**.
