import { Locator, Page } from 'playwright';
import { assertSafeToClick } from '../capture/browser';
import { captureScreenshots } from '../capture/evidence';
import { parseMoney, round2, toMoney, waitForStableText } from '../capture/price';
import { handleVerification } from '../capture/verification';
import { ActualSelections, CleaningType, Extra, Frequency } from '../types';
import { Adapter, AdapterContext, AdapterResult, emptyPrice, emptyTerms } from './types';

/*
 * Scrub Lou — BookingKoala form (see docs/scrub-lou-form-notes.md).
 * The page prices everything client-side from the selections; the "Booking Summary"
 * panel shows TOTAL before tax and TOTAL with tax. We stop there: contact, address,
 * date, card and "Save Booking" are never touched.
 */

const SERVICE_LABELS: Record<CleaningType, string> = {
  standard: 'Routine Cleaning',
  deep: 'Deep Clean',
  move_in_out: 'Move-In/Move-Out Cleaning',
};

const FREQUENCY_LABELS: Record<Frequency, string> = {
  one_time: 'One-Time',
  weekly: 'Weekly',
  biweekly: 'Every Other Week',
  every_4_weeks: 'Every 4 Weeks',
};

const EXTRA_LABELS: Record<Extra, string> = {
  oven_interior: 'Inside Oven',
  fridge_interior: 'Inside Fridge',
  interior_windows: 'Interior Windows (Glass Only)',
  basement: 'Basement',
};

const SEL = {
  zip: '#zipcode-value',
  serviceSelect: 'select:has(option:text-is("Routine Cleaning"))',
  frequencyRadios: 'input[name="frequency"]',
  bedroomsSelect: 'xpath=//*[normalize-space(text())="Bedrooms"]/following::select[1]',
  bathroomsSelect: 'xpath=//*[normalize-space(text())="Bathrooms"]/following::select[1]',
  sqftSelect: 'xpath=//*[normalize-space(text())="Sq Ft"]/following::select[1]',
  extras: 'input.bk-form-extra-input',
  petsNone: 'input[id$="_None"]',
  summaryPanel: '.tjs-summary',
  summaryHeader: '.bk-form-summary-header.tjs-summary-head',
  summaryBody: '#booking-summary',
  summaryRows: '#booking-summary li',
  totalBeforeTax: '#booking-summary .bk-form-sum-tbt-value',
  total: '#booking-summary .bk-form-sum-total-value',
  email: '#userEmail',
};

const norm = (s: string | null | undefined) => (s ?? '').replace(/\s+/g, ' ').replace(/\s*-\s*/g, ' - ').trim().toLowerCase();

export const scrubLouAdapter: Adapter = {
  id: 'scrub-lou',

  async capture(ctx: AdapterContext): Promise<AdapterResult> {
    const { page, settings, company, home, scenario } = ctx;
    const actual: ActualSelections = { extras: [], notes: [] };
    const price = emptyPrice();
    const terms = emptyTerms();
    const result = (status: AdapterResult['status'], statusDetail: string, extra: Partial<AdapterResult> = {}): AdapterResult => ({
      status,
      statusDetail,
      sourceUrl: page.url() || company.formUrl,
      actual,
      price,
      terms,
      screenshotPath: null,
      summaryScreenshotPath: null,
      capturedPriceText: '',
      summaryRows: [],
      ...extra,
    });

    // 1. Open the form
    await page.goto(company.formUrl, { waitUntil: 'domcontentloaded' });
    const zip = page.locator(SEL.zip);
    await zip.waitFor({ state: 'visible' });

    const challenge = await handleVerification(page, ctx.interactive);
    if (challenge) return withShots(ctx, result('verification_required', challenge));

    // 2. Scope checks before touching the form
    if (scenario.areasOnly?.length) {
      return result(
        'not_implemented',
        'Scrub Lou supports partial cleaning by excluding areas ("I want to exclude some areas of my home!": Bedroom, Full Bathroom, Half Bathroom, Kitchen, Living Room). Adapter support is planned for step 5.',
      );
    }

    // 3. ZIP — pricing and tax are keyed to it. Wait for the site's tax lookup for this ZIP.
    const taxResponse = page
      .waitForResponse((r) => r.url().includes('get-tax-rate') && r.url().includes(`postal_code=${home.zip}`), { timeout: 15000 })
      .catch(() => null);
    await zip.fill(home.zip);
    await zip.press('Tab');
    actual.zip = home.zip;
    const taxResp = await taxResponse;
    if (taxResp) {
      try {
        const body = await taxResp.json();
        const rate = body?.response?.data?.tax_rate;
        if (typeof rate === 'number') price.taxRatePercent = rate;
      } catch {
        /* ignore */
      }
    } else {
      actual.notes.push('Tax-rate lookup for ZIP was not observed; price may reflect default location.');
    }
    const areaMsg = await page.getByText(/(don't|do not|doesn't|does not) (service|serve)|not (in|within) our service area|outside (of )?our service area/i).first();
    if (await areaMsg.isVisible().catch(() => false)) {
      return withShots(ctx, result('manual_quote_required', `ZIP ${home.zip} not serviced: ${await areaMsg.innerText()}`));
    }

    // 4. Service type (must precede Sq Ft: the Sq Ft options change by service)
    const serviceLabel = SERVICE_LABELS[scenario.cleaningType];
    await page.locator(SEL.serviceSelect).selectOption({ label: serviceLabel });
    actual.cleaningType = serviceLabel;

    // 5. Frequency
    const freqLabel = FREQUENCY_LABELS[scenario.frequency];
    const freqIdx = await page.locator(SEL.frequencyRadios).evaluateAll(
      (els, label) => els.findIndex((e) => (e.parentElement?.textContent ?? '').replace(/\s+/g, ' ').trim() === label),
      freqLabel,
    );
    if (freqIdx < 0) return withShots(ctx, result('unsupported_option', `Frequency "${freqLabel}" not offered`));
    await checkInput(page.locator(SEL.frequencyRadios).nth(freqIdx));
    actual.frequency = freqLabel;

    // 6. Bedrooms / bathrooms
    const bed = await selectExact(page.locator(SEL.bedroomsSelect), String(home.bedrooms));
    if (!bed) return withShots(ctx, result('manual_quote_required', `Bedrooms ${home.bedrooms} not offered (form max shown in options)`));
    actual.bedrooms = bed;
    const bath = await selectExact(page.locator(SEL.bathroomsSelect), String(home.bathrooms));
    if (!bath) return withShots(ctx, result('manual_quote_required', `Bathrooms ${home.bathrooms} not offered`));
    actual.bathrooms = bath;

    // 7. Square footage → the range bucket that contains it
    const sqftSelect = page.locator(SEL.sqftSelect);
    const sqftOptions = await sqftSelect.locator('option').allInnerTexts();
    const bucket = sqftOptions.find((o) => {
      const m = o.replace(/,/g, '').match(/(\d+)\s*-\s*(\d+)/);
      return m ? home.squareFeet >= Number(m[1]) && home.squareFeet <= Number(m[2]) : false;
    });
    if (!bucket) {
      return withShots(ctx, result('manual_quote_required', `${home.squareFeet} sq ft is outside the online ranges (${sqftOptions[0]} … ${sqftOptions.at(-1)}) for ${serviceLabel}`));
    }
    await sqftSelect.selectOption({ label: bucket });
    actual.squareFeet = bucket.trim();

    // 8. Condition / pets — Scrub Lou has no condition field; pets don't change price but we record "None"
    actual.condition = '';
    actual.notes.push('Form has no home-condition field; requested condition not applied.');
    const petsNone = page.locator(SEL.petsNone).first();
    if (await petsNone.count()) {
      await checkInput(petsNone).catch(() => undefined);
      actual.pets = 'None';
    }

    // 9. Extras
    const extraNames = await page.locator(SEL.extras).evaluateAll((els) =>
      els.map((e) => {
        let p: Element | null = e;
        for (let i = 0; i < 6 && p && !(p.textContent ?? '').trim(); i++) p = p.parentElement;
        return (p?.textContent ?? '').replace(/\s+/g, ' ').trim();
      }),
    );
    for (const extra of scenario.extras) {
      const label = EXTRA_LABELS[extra];
      const idx = extraNames.findIndex((n) => n === label);
      if (idx < 0) return withShots(ctx, result('unsupported_option', `Extra "${label}" not offered`));
      await checkInput(page.locator(SEL.extras).nth(idx));
      actual.extras.push(label);
    }

    // 10. Expand the Booking Summary and wait for the price to settle
    await expandSummary(page, ctx);
    const readPrice = async () =>
      [
        await page.locator(SEL.totalBeforeTax).first().innerText().catch(() => ''),
        await page.locator(SEL.total).first().innerText().catch(() => ''),
        await page.locator(SEL.summaryRows).allInnerTexts().then((t) => t.join('|')).catch(() => ''),
      ].join(' || ');
    try {
      await waitForStableText(page, readPrice, { stableMs: settings.timing.priceStableMs, timeoutMs: settings.timing.priceTimeoutMs });
    } catch (err) {
      return withShots(ctx, result('extraction_failed', (err as Error).message));
    }

    // 11. Read the summary
    // Leaf rows only: the Extras block nests its own <li> items.
    const rows = await page.locator(SEL.summaryRows).evaluateAll((lis) =>
      lis
        .filter((li) => !li.querySelector('li'))
        .map((li) => {
          const label = (li.querySelector('.bk-form-sum-label')?.textContent ?? '').replace(/\s+/g, ' ').trim();
          const desc = li.querySelector('.bk-form-sum-desc');
          const value = ((desc ? desc.textContent : li.textContent?.replace(label, '')) ?? '').replace(/\s+/g, ' ').trim();
          return { label, value, group: li.closest('.tjs-summary-extras') ? 'extra' : '' };
        }),
    );
    const tbtText = (await page.locator(SEL.totalBeforeTax).first().innerText().catch(() => '')).trim();
    const totalText = (await page.locator(SEL.total).first().innerText().catch(() => '')).trim();
    const capturedPriceText = (await page.locator(SEL.summaryPanel).first().innerText().catch(() => '')).replace(/\s+/g, ' ').trim();

    // 12. Verify the summary reflects what we selected (guards against stale prices)
    const want: [string, string][] = [
      ['Service', serviceLabel],
      ['Frequency', freqLabel],
      ['Bedrooms', bed],
      ['Bathrooms', bath],
      ['Sq Ft', bucket],
    ];
    const mismatches = want
      .map(([label, expected]) => {
        const row = rows.find((r) => norm(r.label) === norm(label));
        return row && norm(row.value).replace(/ - /g, '-') === norm(expected).replace(/ - /g, '-') ? null : `${label}: expected "${expected}", summary shows "${row?.value ?? '(missing)'}"`;
      })
      .filter(Boolean) as string[];
    for (const label of actual.extras) if (!rows.some((r) => r.group === 'extra' && norm(r.label) === norm(label))) mismatches.push(`Extra "${label}" missing from summary`);

    // 13. Price breakdown
    price.displayedTotal = toMoney(totalText);
    price.totalBeforeTax = toMoney(tbtText);
    for (const r of rows) {
      if (r.group === 'extra') {
        price.extras.push({ label: r.label, amount: parseMoney(r.value), text: r.value });
        continue;
      }
      const kind = /discount|coupon|% off|savings/i.test(r.label) ? 'discount' : /tax/i.test(r.label) ? 'tax' : /fee|charge|surcharge/i.test(r.label) ? 'fee' : null;
      if (!kind) continue;
      if (kind === 'tax') {
        price.tax = toMoney(r.value);
        price.taxNote = 'Tax shown as a summary line.';
      } else {
        (kind === 'discount' ? price.discounts : price.fees).push({ label: r.label, amount: parseMoney(r.value), text: r.value });
      }
    }
    if (!price.tax && price.displayedTotal && price.totalBeforeTax && price.displayedTotal.amount > price.totalBeforeTax.amount) {
      const t = round2(price.displayedTotal.amount - price.totalBeforeTax.amount);
      price.tax = { amount: t, text: t.toFixed(2) };
      price.taxNote = `Derived: displayed total minus displayed pre-tax total${price.taxRatePercent !== null ? ` (site tax rate ${price.taxRatePercent}%)` : ''}.`;
    }

    // 14. Terms visible on the page
    const pageText = (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ');
    if (/recommend a deep clean for your first clean/i.test(pageText)) {
      terms.firstCleanRequirement = 'Recommended, not required: deep clean for the first recurring clean.';
    }
    if (scenario.frequency !== 'one_time') {
      terms.priceQualifications.push('Summary shows a single per-visit total; no separate first-visit vs. subsequent-visit price is displayed.');
    }
    const quals: [RegExp, string][] = [
      [/credit cards will not be charged until all services have been completed/i, 'Card charged after service is completed.'],
      [/temporary hold will be placed on the card 24 hours prior/i, 'Temporary card hold 24 hours before appointment.'],
      [/indicate the entire home size first/i, 'Price based on whole-home size; areas can be excluded.'],
    ];
    for (const [re, note] of quals) if (re.test(pageText)) terms.priceQualifications.push(note);

    // 15. Safety check: we never entered contact details
    const emailVal = await page.locator(SEL.email).inputValue().catch(() => '');
    if (emailVal) actual.notes.push('WARNING: email field is not empty.');

    // 16. Evidence
    const shots = await captureScreenshots(page, ctx.evidenceDir, ctx.evidenceBaseName, page.locator(SEL.summaryPanel).first());
    const base: Partial<AdapterResult> = {
      screenshotPath: shots.fullPage,
      summaryScreenshotPath: shots.element,
      capturedPriceText,
      summaryRows: rows.map(({ label, value, group }) => ({ label: group ? `${group}: ${label}` : label, value })),
    };
    if (!price.displayedTotal) return result('extraction_failed', `No total found (text: "${totalText}")`, base);
    if (mismatches.length) return result('extraction_failed', `Summary does not match selections: ${mismatches.join('; ')}`, base);
    return result('success', `Captured ${price.displayedTotal.text} (before tax ${price.totalBeforeTax?.text ?? 'n/a'})`, base);
  },
};

/** Checks a radio/checkbox; falls back to clicking its wrapper when the input is visually hidden. */
async function checkInput(input: Locator): Promise<void> {
  try {
    await input.check({ force: true, timeout: 5000 });
  } catch {
    await input.locator('xpath=..').click();
  }
  if (!(await input.isChecked())) throw new Error('Could not select form option');
}

async function selectExact(select: Locator, label: string): Promise<string | null> {
  const options = (await select.locator('option').allInnerTexts()).map((o) => o.trim());
  const match = options.find((o) => o === label);
  if (!match) return null;
  await select.selectOption({ label: match });
  return match;
}

async function expandSummary(page: Page, ctx: AdapterContext): Promise<void> {
  const body = page.locator(SEL.summaryBody);
  if (await body.isVisible().catch(() => false)) return;
  const header = page.locator(SEL.summaryHeader).first();
  if (await header.isVisible().catch(() => false)) {
    await assertSafeToClick(page, SEL.summaryHeader, ctx.settings);
    await header.click();
    await body.waitFor({ state: 'visible', timeout: 5000 }).catch(() => undefined);
  }
}

/** On early exits, still save a screenshot so failures have evidence. */
async function withShots(ctx: AdapterContext, r: AdapterResult): Promise<AdapterResult> {
  const shots = await captureScreenshots(ctx.page, ctx.evidenceDir, ctx.evidenceBaseName);
  return { ...r, screenshotPath: shots.fullPage, sourceUrl: ctx.page.url() || r.sourceUrl };
}
