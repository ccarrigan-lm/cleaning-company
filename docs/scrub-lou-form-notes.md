# Scrub Lou: quote form notes

Inspected 2026-10-13 using ZIP 40217.

## Where the form lives
- Public page: https://scrublou.com/book-now/ ("Get Free Estimate" buttons on the home page link to `/#book`.)
- The form is a **BookingKoala iframe**: `https://scrublou.bookingkoala.com/booknow?embed=true`.
- The adapter loads `https://scrublou.bookingkoala.com/booknow` directly, which is the same form without the iframe.
- It's an Angular app. Prices are calculated in the browser from the selections, so changing inputs doesn't send an inquiry.

## Inputs (in page order)
| Field | Control | Options |
|---|---|---|
| ZIP | `#zipcode-value` text | Sets location pricing and tax (calls `GET /api/v4/get-tax-rate?postal_code=…`) |
| Service Type | select | Routine Cleaning, Deep Clean, Move-In/Move-Out Cleaning |
| Frequency | radio `name=frequency` | One-Time, Weekly, Every Other Week (default), Every 4 Weeks |
| Bedrooms | select | 1–5 |
| Bathrooms | select | 1, 1.5, 2 … 5 |
| Sq Ft | select (ranges) | Routine: 1–999 … 5500–5999. Deep Clean: 1–999 … 4500–4999. The option list changes with the service type. |
| Partial home | checkbox `#partial_cleaning` ("I want to exclude some areas of my home!") | Exclude: Bedroom, Full Bathroom, Half Bathroom, Kitchen, Living Room |
| Extras | checkboxes `.bk-form-extra-input` | Interior Windows (Glass Only), Basement, Interior Windows (Glass & Tracks), Inside Oven ($45), Inside Fridge |
| Pets | checkboxes | Dog(s), Cat(s), None |
| Condition | — | **No field.** |

## When the price appears and what changes it
- The **Booking Summary** panel on the right shows a price as soon as the page loads. That price uses default inputs and the default tax, so it isn't valid until the ZIP is entered and the tax lookup returns.
- The summary has two totals, both labeled "TOTAL":
  - `.bk-form-sum-tbt-value` is the **total before tax**
  - `.bk-form-sum-total-value` is the **total including tax** (6% in 40217)
- Every Other Week shows 15% less than One-Time (169.00 → 143.65 for 1bd/1ba). The summary has no discount line and shows one per-visit total, so it doesn't say whether the first visit gets the discount.
- Extras show as their own lines under "Extras" (e.g. Inside Oven 45.00).
- The page recommends, but doesn't require, a Deep Clean as the first clean for recurring service.

## Contact, account, address
- **None of them are needed to see a price.** First/last name, email, phone, address, date and card are only for booking.
- Disclaimer: "By entering any information, you … authorize BookingKoala … to deliver marketing." The adapter never fills any contact field.

## Where automation must stop
- Everything below **Choose Service Date & Time** is booking territory: customer details, address, key info, coupon, payment (Stripe card), terms checkbox, and **Save Booking**.
- **Save Booking** commits the booking, and the card is held 24h before the appointment. The adapter never clicks it. The network guard also blocks booking, lead, customer and Stripe payment POSTs.

## Manual reference quote (spot-check)
ZIP 40217, Routine Cleaning, One-Time, 3 bd / 2 ba / 1500–1999 sq ft, no extras, no pets:
**$249.00 before tax, $263.94 total (6% tax).**
Adding Inside Oven: $294.00 / $311.64.
