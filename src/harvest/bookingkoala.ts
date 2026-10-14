import fs from 'fs';
import path from 'path';
import { Page } from 'playwright';

/**
 * Full-grid harvester for BookingKoala booking forms (Scrub Lou, Maids in Apron, ...).
 *
 * BookingKoala prices everything in the browser, so changing selections sends no inquiry.
 * After the ZIP is entered, this walks every service × frequency × bedrooms × bathrooms × sq ft
 * option inside the page and reads the Booking Summary for each combination. A row is only
 * marked verified when the summary shows exactly the options that were selected.
 *
 * Never touches contact, address, date or payment fields, and never clicks Save Booking.
 */
export interface BkHarvestOptions {
  formUrl: string;
  zip: string;
  /** Label text of the size selects. Detected from the form when omitted. */
  labels?: { bedrooms: string; bathrooms: string; sqft: string };
  /** Only harvest these service names (default: all options in the service select). */
  services?: string[];
  frequencies?: string[];
  /** Stop a company after this many combinations (protects against huge forms). */
  maxCombos?: number;
  /** Epoch ms: stop and return what was collected so far. */
  deadline?: number;
}

export interface BkRow {
  service: string;
  frequency: string;
  bedrooms: string;
  bathrooms: string;
  sqft: string;
  /** Any other price-changing select on the form, as "Label=Value; Label=Value". */
  otherOptions: string;
  totalBeforeTax: string; // blank when the site shows only one total
  total: string; // first visit total as displayed (tax included when the site adds it)
  recurringTotal: string; // "Recurring Total" when shown
  verified: boolean;
}

export interface BkFormInfo {
  services: string[];
  frequencies: string[];
  dims: { key: string; label: string; options: number }[];
  zipFound: boolean;
}

export async function harvestBookingKoala(page: Page, opts: BkHarvestOptions, log = console.log): Promise<{ rows: BkRow[]; taxRate: number | null; form: BkFormInfo; partial: boolean; skipped: string[] }> {
  await page.goto(opts.formUrl, { waitUntil: 'domcontentloaded' });
  const zip = page.locator('#zipcode-value');
  const zipFound = await zip.waitFor({ state: 'visible', timeout: 15000 }).then(() => true).catch(() => false);
  let taxRate: number | null = null;
  if (zipFound) {
    const taxResp = page.waitForResponse((r) => r.url().includes('get-tax-rate') && r.url().includes(`postal_code=${opts.zip}`), { timeout: 20000 }).catch(() => null);
    await zip.fill(opts.zip);
    await zip.press('Tab');
    const tr = await taxResp;
    if (tr) taxRate = (await tr.json().catch(() => null))?.response?.data?.tax_rate ?? null;
    else log('  [warn] tax lookup for ZIP not observed; prices may use the default location');
  } else {
    log('  [warn] no ZIP field on this form; prices are the default location');
    await page.locator('#booking-summary').first().waitFor({ timeout: 20000 }).catch(() => undefined);
  }
  await page.waitForTimeout(1500);

  // Install the in-page driver. Selects are found by the text label in front of them.
  await page.evaluate(() => {
    const mc = new MessageChannel();
    const q: Array<() => void> = [];
    mc.port1.onmessage = () => q.shift()?.();
    const labelOf = (s: Element) => {
      const r = document.evaluate('preceding::*[normalize-space(text())][1]', s, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue as HTMLElement | null;
      return (r?.textContent || '').replace(/\s+/g, ' ').replace(/[*:]/g, '').trim();
    };
    const visible = (e: Element) => !!(e as HTMLElement).offsetParent || (e as HTMLElement).getClientRects().length > 0;
    const allSelects = () => [...document.querySelectorAll('select')].filter((s) => visible(s) && !s.closest('#booking-summary')) as HTMLSelectElement[];
    const isService = (s: HTMLSelectElement) => s.options.length > 0 && !/^\d/.test(s.options[0].text.trim()) && !/sq|select option|bed|bath/i.test(s.options[0].text + labelOf(s));
    const isBookingField = (s: HTMLSelectElement) => /state|country|time|date|month|year|hour|minute|key|park|how did|hear|referr|source|tip|inside|access|entry|enter|get in|let us know|lockbox|garage code/i.test(labelOf(s));
    (window as any).__bk = {
      labelOf,
      svc: () => allSelects().find((s) => isService(s) && !isBookingField(s)),
      byLabel: (label: string) => allSelects().find((s) => labelOf(s) === label),
      dimSelects() {
        const svc = this.svc();
        return allSelects().filter((s) => s !== svc && !isBookingField(s) && s.options.length > 1);
      },
      setSel(s: HTMLSelectElement, i: number) {
        if (s && s.selectedIndex !== i) {
          s.selectedIndex = i;
          s.dispatchEvent(new Event('change', { bubbles: true }));
        }
      },
      freqs: () => [...document.querySelectorAll('input[name=frequency]')].map((e) => e.parentElement!.textContent!.trim()),
      setFreq(label: string) {
        const r = [...document.querySelectorAll('input[name=frequency]')].find((e) => e.parentElement!.textContent!.trim() === label) as HTMLInputElement;
        if (r && !r.checked) r.click();
      },
      tick: () => new Promise<void>((r) => { q.push(r); mc.port2.postMessage(0); }),
      read() {
        const g = (s: string) => document.querySelector('#booking-summary ' + s)?.textContent?.trim() || '';
        const rows = [...document.querySelectorAll('#booking-summary li')].filter((l) => !l.querySelector('li')).map((l) => l.textContent!.replace(/\s+/g, ' ').trim()).join('|');
        return [g('.bk-form-sum-tbt-value'), g('.bk-form-sum-total-value'), g('.bk-form-sum-fst-apt-value'), rows].join('#');
      },
      async settle(ms = 60) {
        let last = this.read(), since = performance.now();
        const t0 = performance.now();
        while (performance.now() - t0 < 5000) {
          await this.tick();
          const n = this.read();
          if (n !== last) { last = n; since = performance.now(); } else if (performance.now() - since >= ms) return n;
        }
        return last;
      },
    };
  });

  const plan = await page.evaluate(() => {
    const b = (window as any).__bk;
    const svc = b.svc();
    return { services: svc ? [...svc.options].map((o: HTMLOptionElement) => o.text.trim()) : ['(single service)'], freqs: b.freqs() as string[] };
  });
  const services = plan.services.filter((s: string) => !opts.services || opts.services.includes(s));
  const freqs = plan.freqs.filter((f: string) => !opts.frequencies || opts.frequencies.includes(f));
  if (!freqs.length) freqs.push('(none)');
  log(`  services: ${services.join(', ')}\n  frequencies: ${freqs.join(', ')}`);

  const rows: BkRow[] = [];
  let form: BkFormInfo = { services, frequencies: freqs, dims: [], zipFound };
  const maxCombos = opts.maxCombos ?? 60000;
  const deadline = opts.deadline ?? Number.MAX_SAFE_INTEGER;
  const skipped: string[] = [];
  for (const service of services) {
    for (const freq of freqs) {
      if (rows.length >= maxCombos) {
        log(`  [warn] stopped at ${maxCombos} combinations (maxCombos)`);
        return { rows, taxRate, form, partial: true, skipped };
      }
      if (Date.now() > deadline) {
        log('  [warn] time limit reached; keeping what was collected');
        return { rows, taxRate, form, partial: true, skipped };
      }
      const chunk: { dims: BkFormInfo['dims']; rows: BkRow[]; unavailable: boolean; timedOut: boolean } = await page.evaluate(
        async ({ service, freq, labels, cap, deadline }) => {
          const b = (window as any).__bk;
          const svc = b.svc();
          if (svc && service !== '(single service)') b.setSel(svc, [...svc.options].findIndex((o: HTMLOptionElement) => o.text.trim() === service));
          await b.settle();
          if (freq !== '(none)') b.setFreq(freq);
          await b.settle();
          // Price-changing selects for this service, classified by their label.
          const sels: HTMLSelectElement[] = b.dimSelects();
          const dims = sels.map((s) => {
            const label = b.labelOf(s) as string;
            let key = 'other';
            if (labels ? label === labels.bedrooms : /bed/i.test(label)) key = 'bedrooms';
            else if (labels ? label === labels.bathrooms : /bath/i.test(label) && !/half/i.test(label)) key = 'bathrooms';
            else if (labels ? label === labels.sqft : /sq|feet|footage|size|area/i.test(label)) key = 'sqft';
            return { key, label, options: s.options.length };
          });
          const out: any[] = [];
          const norm = (s: string) => s.replace(/\s+/g, '').toLowerCase();
          const idx = dims.map(() => 0);
          const total = dims.reduce((n, d) => n * d.options, 1);
          let unavailable = false, timedOut = false;
          for (let c = 0; c < total && out.length < cap; c++) {
            if (Date.now() > deadline) { timedOut = true; break; }
            // The summary never matches for a service/frequency pair the form doesn't offer
            // (e.g. move-out on a weekly schedule). Give up on the pair after 20 straight misses.
            if (out.length === 20 && out.every((o) => !o.verified)) { unavailable = true; break; }
            let rem = c;
            for (let d = dims.length - 1; d >= 0; d--) { idx[d] = rem % dims[d].options; rem = Math.floor(rem / dims[d].options); }
            const cur: HTMLSelectElement[] = dims.map((d) => b.byLabel(d.label));
            cur.forEach((s, d) => b.setSel(s, idx[d]));
            const vals = cur.map((s, d) => (s ? s.options[idx[d]].text.trim() : ''));
            let r = '', ok = false;
            for (let a = 0; a < (out.length < 20 || out.some((o) => o.verified) ? 4 : 1) && !ok; a++) {
              r = await b.settle();
              const ns = norm(r.split('#')[3] + '|');
              ok = (freq === '(none)' || ns.includes(norm(`Frequency ${freq}`) + '|')) &&
                dims.every((d, i) => d.key === 'other' || ns.includes(norm(`${d.label} ${vals[i]}`) + '|'));
            }
            const [tbt, tot, rec] = r.split('#');
            const pick = (k: string) => { const i = dims.findIndex((d) => d.key === k); return i < 0 ? '' : vals[i]; };
            out.push({
              service, frequency: freq, bedrooms: pick('bedrooms'), bathrooms: pick('bathrooms'), sqft: pick('sqft'),
              otherOptions: dims.map((d, i) => (d.key === 'other' ? `${d.label}=${vals[i]}` : '')).filter(Boolean).join('; '),
              totalBeforeTax: tbt, total: tot, recurringTotal: rec, verified: ok,
            });
          }
          return { dims, rows: unavailable ? [] : out, unavailable, timedOut };
        },
        { service, freq, labels: opts.labels ?? null, cap: maxCombos - rows.length, deadline },
      );
      form = { ...form, dims: chunk.dims };
      if (chunk.unavailable) {
        skipped.push(`${service} / ${freq}`);
        log(`  ${service} / ${freq}: not offered on the form (summary never matched), skipped`);
        continue;
      }
      rows.push(...chunk.rows);
      if (chunk.timedOut) {
        log('  [warn] time limit reached; keeping what was collected');
        return { rows, taxRate, form, partial: true, skipped };
      }
      log(`  ${service} / ${freq}: ${chunk.rows.length} combinations over [${chunk.dims.map((d) => `${d.label}(${d.options})`).join(' x ')}] (${chunk.rows.filter((c) => !c.verified).length} unverified)`);
    }
  }
  return { rows, taxRate, form, partial: false, skipped };
}

export function writeRows(dir: string, base: string, rows: object[]): { csv: string; json: string } {
  fs.mkdirSync(dir, { recursive: true });
  const json = path.join(dir, `${base}.json`);
  fs.writeFileSync(json, JSON.stringify(rows, null, 1));
  const keys = rows.length ? Object.keys(rows[0]) : [];
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = path.join(dir, `${base}.csv`);
  fs.writeFileSync(csv, '﻿' + [keys.join(','), ...rows.map((r: any) => keys.map((k) => esc(r[k])).join(','))].join('\r\n'));
  return { csv, json };
}
