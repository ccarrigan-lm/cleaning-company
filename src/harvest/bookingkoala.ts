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
  /** Label text of the size selects on this form. */
  labels: { bedrooms: string; bathrooms: string; sqft: string };
  /** Only harvest these service names (default: all options in the service select). */
  services?: string[];
  frequencies?: string[];
}

export interface BkRow {
  service: string;
  frequency: string;
  bedrooms: string;
  bathrooms: string;
  sqft: string;
  totalBeforeTax: string; // blank when the site shows only one total
  total: string; // first visit total as displayed (tax included when the site adds it)
  recurringTotal: string; // "Recurring Total" when shown
  verified: boolean;
}

export async function harvestBookingKoala(page: Page, opts: BkHarvestOptions, log = console.log): Promise<{ rows: BkRow[]; taxRate: number | null }> {
  await page.goto(opts.formUrl, { waitUntil: 'domcontentloaded' });
  const zip = page.locator('#zipcode-value');
  await zip.waitFor({ state: 'visible' });
  const taxResp = page.waitForResponse((r) => r.url().includes('get-tax-rate') && r.url().includes(`postal_code=${opts.zip}`), { timeout: 20000 }).catch(() => null);
  await zip.fill(opts.zip);
  await zip.press('Tab');
  let taxRate: number | null = null;
  const tr = await taxResp;
  if (tr) taxRate = (await tr.json().catch(() => null))?.response?.data?.tax_rate ?? null;
  else log('  [warn] tax lookup for ZIP not observed; prices may use the default location');

  // Install the in-page driver (same logic used for the October 2026 capture).
  await page.evaluate((labels) => {
    const mc = new MessageChannel();
    const q: Array<() => void> = [];
    mc.port1.onmessage = () => q.shift()?.();
    const x = (p: string) => document.evaluate(p, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue as HTMLSelectElement;
    const sel = (label: string) => x(`//*[normalize-space(text())="${label}"]/following::select[1]`);
    (window as any).__bk = {
      svc: () => [...document.querySelectorAll('select')].find((s) => (s as HTMLSelectElement).options.length > 0 && !/^\d/.test((s as HTMLSelectElement).options[0].text.trim()) && !/sq|select option/i.test((s as HTMLSelectElement).options[0].text)) as HTMLSelectElement,
      bed: () => sel(labels.bedrooms),
      bath: () => sel(labels.bathrooms),
      sq: () => sel(labels.sqft),
      setSel(s: HTMLSelectElement, i: number) {
        if (s.selectedIndex !== i) {
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
  }, opts.labels);

  const plan = await page.evaluate(() => {
    const b = (window as any).__bk;
    const svc = b.svc();
    return { services: svc ? [...svc.options].map((o: HTMLOptionElement) => o.text.trim()) : ['(single service)'], freqs: b.freqs() };
  });
  const services = plan.services.filter((s: string) => !opts.services || opts.services.includes(s));
  const freqs = plan.freqs.filter((f: string) => !opts.frequencies || opts.frequencies.includes(f));
  log(`  services: ${services.join(', ')}\n  frequencies: ${freqs.join(', ')}`);

  const rows: BkRow[] = [];
  for (const service of services) {
    for (const freq of freqs) {
      const chunk: BkRow[] = await page.evaluate(
        async ({ service, freq, labels }) => {
          const b = (window as any).__bk;
          const svc = b.svc();
          if (svc) b.setSel(svc, [...svc.options].findIndex((o: HTMLOptionElement) => o.text.trim() === service));
          await b.settle();
          b.setFreq(freq);
          await b.settle();
          const out: any[] = [];
          const norm = (s: string) => s.replace(/\s+/g, '').toLowerCase();
          const nb = b.bed().options.length, nba = b.bath().options.length, nsq = b.sq().options.length;
          for (let i = 0; i < nb; i++) for (let j = 0; j < nba; j++) for (let k = 0; k < nsq; k++) {
            b.setSel(b.bed(), i); b.setSel(b.bath(), j); b.setSel(b.sq(), k);
            const bed = b.bed().options[i].text.trim(), bath = b.bath().options[j].text.trim(), sq = b.sq().options[k].text.trim();
            let r = '', ok = false;
            for (let a = 0; a < 4 && !ok; a++) {
              r = await b.settle();
              const s = r.split('#')[3] + '|';
              const ns = norm(s);
              ok =
                ns.includes(norm(`Frequency ${freq}`) + '|') &&
                ns.includes(norm(`${labels.bedrooms} ${bed}`) + '|') &&
                ns.includes(norm(`${labels.bathrooms} ${bath}`) + '|') &&
                ns.includes(norm(`${labels.sqft} ${sq}`) + '|');
            }
            const [tbt, tot, rec] = r.split('#');
            out.push({ service, frequency: freq, bedrooms: bed, bathrooms: bath, sqft: sq, totalBeforeTax: tbt, total: tot, recurringTotal: rec, verified: ok });
          }
          return out;
        },
        { service, freq, labels: opts.labels },
      );
      rows.push(...chunk);
      log(`  ${service} / ${freq}: ${chunk.length} combinations (${chunk.filter((c) => !c.verified).length} unverified)`);
    }
  }
  return { rows, taxRate };
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
