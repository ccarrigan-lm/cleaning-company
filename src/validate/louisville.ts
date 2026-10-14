import fs from 'fs';
import path from 'path';
import { Page } from 'playwright';
import { launch } from '../capture/browser';
import { Settings } from '../config';

/**
 * Louisville-only live validation (npm run validate:louisville).
 *
 * Reads prices from the live booking forms only. It types the pricing ZIP and changes the
 * price selectors; it never fills contact, address, date or payment fields and never
 * clicks a booking/submit button (the network guard also blocks booking POSTs).
 *
 *  1. Red Feather (BookingKoala): move-out re-capture; bedrooms and bathrooms varied one at a
 *     time at a fixed sq ft band; same home under Deep and Basic; move-out on a recurring schedule.
 *  2. Maid 2 Clean KY: tries the Launch27 host recorded by discovery, then the booking iframe on
 *     maid2cleanky.com/booking-page/, and reads the home-page price widget.
 *  3. Launch27 spot checks (Super Cleaning, Maid 2 Clean): small / typical / larger home x
 *     one-time standard, biweekly, one-time deep. Observed vs calculated from the site's own feed.
 *
 * Output: output/validation/<stamp>/{results.json, results.csv, screenshots/*.png}
 */

interface Obs {
  company: string;
  test: string;
  inputs: Record<string, string | boolean>;
  observed: Record<string, number | string | null>;
  calculated: number | null;
  calcSource: string;
  match: string;
  summaryText: string;
  url: string;
  timestamp: string;
  screenshot: string;
}

const HOMES = [
  { id: 'small', l27: { super: ['One Bedroom Home', '1-999 sq ft', '1 Bathroom', '0 Half-bathrooms'], m2: ['One Bedroom Home', '1 Bathroom', ''] } },
  { id: 'typical', l27: { super: ['Three Bedroom Home', '1500-1999 sq ft', '2 Bathrooms', '0 Half-bathrooms'], m2: ['Three Bedroom Home', '2 Bathrooms', 'Over 1500 sq.ft'] } },
  { id: 'larger', l27: { super: ['Four Bedroom Home', '3000-3499 sq ft', '3 Bathrooms', '0 Half-bathrooms'], m2: ['Four Bedroom Home', '3 Bathrooms', 'Over 3000 sq.ft'] } },
];

const num = (s: string | undefined | null) => {
  const m = (s || '').replace(/,/g, '').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
};

async function settle(page: Page, read: () => Promise<string>, quietMs = 2000, maxMs = 15000): Promise<string> {
  let last = await read();
  let since = Date.now();
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    await page.waitForTimeout(250);
    const n = await read();
    if (n !== last) {
      last = n;
      since = Date.now();
    } else if (Date.now() - since > quietMs) break;
  }
  return last;
}

// ------------------------------------------------------------------------------------------- Launch27 helpers
async function l27Feed(page: Page) {
  return page.evaluate(async () => {
    const get = (u: string) => fetch(u, { headers: { Accept: 'application/json' } }).then(async (r) => ({ status: r.status, body: r.ok ? await r.json() : await r.text() }));
    return { services: await get('/v1/booking/services?location_id=1&mode=tags'), frequencies: await get('/v1/booking/frequencies?location_id=1') };
  });
}

function l27Calc(feed: any, service: string, picks: Record<string, string>, freqName: string, addOnPrefix: string | null) {
  const svc = feed.services.body.services.find((s: any) => s.name === service);
  if (!svc) return null;
  let p = Number(svc.price);
  for (const prm of svc.pricing_parameters || []) {
    if (prm.type === 'ranged') {
      const r = prm.ranges.find((x: any) => Object.values(picks).includes(x.label));
      p += r ? Number(r.price) : 0;
    } else {
      const want = Object.values(picks).find((v) => new RegExp(prm.name.replace(/-?s$/i, ''), 'i').test(v) && /^\d/.test(v));
      const qty = want ? parseInt(want, 10) : Number(prm.quantity_minimum || 0);
      p += qty * Number(prm.price);
    }
  }
  if (addOnPrefix) {
    const e = (svc.extras || []).find((x: any) => x.name.startsWith(addOnPrefix));
    p += e ? Number(e.price) : 0;
  }
  const f = (feed.frequencies.body || []).find((x: any) => x.name === freqName);
  const m = 1 - (Number(f?.percent) || 0) / 100;
  return Math.round(p * (f?.exclude_first ? 1 : m) * 100) / 100;
}

async function l27Panel(page: Page): Promise<string> {
  return page.evaluate(() => {
    const leaf = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && /^booking summary$/i.test((e.textContent || '').trim()));
    let p = leaf as HTMLElement | null;
    while (p && !/TOTAL/i.test(p.innerText)) p = p.parentElement;
    return p ? p.innerText.split('\n').map((s) => s.trim()).filter(Boolean).join(' | ') : '';
  });
}

async function l27Select(page: Page, optionText: string) {
  const ok = await page.evaluate((t) => {
    const vis = [...document.querySelectorAll('select')].filter((s) => (s as HTMLElement).offsetParent) as HTMLSelectElement[];
    const s = vis.find((x) => [...x.options].some((o) => o.text.trim() === t));
    if (!s) return false;
    s.setAttribute('data-validate-target', '1');
    return true;
  }, optionText);
  if (!ok) throw new Error(`no visible select offers "${optionText}"`);
  const loc = page.locator('select[data-validate-target="1"]');
  await loc.selectOption({ label: optionText });
  await loc.evaluate((s) => s.removeAttribute('data-validate-target'));
}

async function l27Case(page: Page, opts: { service: string; others: string[]; freq: string; deep: boolean }) {
  await l27Select(page, opts.service);
  await page.waitForTimeout(600);
  for (const o of opts.others.filter(Boolean)) await l27Select(page, o);
  await page.locator('.frequency-option', { hasText: opts.freq }).first().click();
  const deepEl = page.locator('.extra-option', { hasText: 'Deep Cleaning' }).first();
  const active = await deepEl.evaluate((e) => /active|selected|checked/.test(e.className + ' ' + (e.parentElement?.className || '')));
  if (active !== opts.deep) await deepEl.click();
  return settle(page, () => l27Panel(page));
}

async function shot(page: Page, dir: string, name: string) {
  const file = path.join(dir, 'screenshots', `${name}.png`);
  await page.screenshot({ path: file, fullPage: false }).catch(() => undefined);
  return path.relative(path.dirname(dir), file);
}

// ------------------------------------------------------------------------------------------- main
export async function validateLouisville(settings: Settings, outRoot: string, log = console.log) {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const dir = path.join(outRoot, 'validation', stamp);
  fs.mkdirSync(path.join(dir, 'screenshots'), { recursive: true });
  const results: Obs[] = [];
  const notes: string[] = [];
  const session = await launch(settings);
  const page = session.page;
  const rec = (o: Omit<Obs, 'timestamp' | 'url'>) => results.push({ ...o, url: page.url(), timestamp: new Date().toISOString() });

  const section = async (name: string, fn: () => Promise<void>) => {
    try {
      await fn();
    } catch (err) {
      notes.push(`ERROR in ${name}: ${(err as Error).message.split('\n')[0]}`);
      log(`  [error] ${name}: ${(err as Error).message.split('\n')[0]} (continuing)`);
    }
  };
  let iframe = '';
  try {
    await section('Red Feather', async () => {
    // ---------------------------------------------------------------- 1. Red Feather
    log('\n[1/3] Red Feather (BookingKoala)');
    await page.goto('https://redfeathercleaning.bookingkoala.com/booknow', { waitUntil: 'domcontentloaded' });
    const zip = page.locator('#zipcode-value');
    await zip.waitFor({ state: 'visible', timeout: 20000 });
    await zip.click();
    await zip.fill('');
    await zip.type('40217', { delay: 60 });
    await zip.press('Tab');
    await page.waitForTimeout(2500);
    const bkSummary = () => page.evaluate(() => (document.querySelector('#booking-summary') as HTMLElement | null)?.innerText.replace(/\s+/g, ' ').trim() || '');
    const bkSel = async (label: string, option: string) => {
      const sel = page.locator(`xpath=//*[normalize-space(text())="${label}"]/following::select[1]`).first();
      await sel.selectOption({ label: option });
    };
    const bkCase = async (test: string, service: string, freq: string, bed: string, bath: string, sq: string, calcNote = '') => {
      await bkSel('Services', service);
      await page.waitForTimeout(500);
      const radio = page.locator('input[name=frequency]').locator(`xpath=..`).filter({ hasText: freq }).locator('input[name=frequency]').first();
      if (await radio.count()) await radio.check({ force: true }).catch(() => undefined);
      await bkSel('Bedrooms', bed);
      await bkSel('Bathrooms', bath);
      await bkSel('Sq Ft', sq);
      const s = await settle(page, bkSummary, 1500);
      const name = `redfeather_${test.replace(/\W+/g, '_')}_${service.replace(/\W+/g, '')}_${bed}bd_${bath}ba`;
      await page.locator('#booking-summary').scrollIntoViewIfNeeded().catch(() => undefined);
      const file = await shot(page, dir, name);
      rec({ company: 'Red Feather Cleaning', test, inputs: { service, frequency: freq, bedrooms: bed, bathrooms: bath, sqft: sq, zip: '40217' },
            observed: { service_shown: (s.match(/Service (.*?) Frequency/) || [])[1] || null, frequency_shown: (s.match(/Frequency (.*?) Bedrooms/) || [])[1] || null,
                        total_before_tax: num((s.match(/Total Before Tax ([\d.,]+)/) || [])[1]), total: num((s.match(/TOTAL ([\d.,]+)/) || [])[1]) },
            calculated: null, calcSource: calcNote || 'n/a (no feed for BookingKoala)', match: '', summaryText: s, screenshot: file });
    };
    for (const b of ['0', '1', '2', '3', '4', '5']) await bkCase('move: bedrooms vary', 'Move In/Out Clean', 'One-Time', b, '2', '1500-1799 Sq Ft');
    for (const ba of ['1', '1.5', '2.5', '3', '4']) await bkCase('move: bathrooms vary', 'Move In/Out Clean', 'One-Time', '3', ba, '1500-1799 Sq Ft');
    for (const s of ['Deep Clean', 'Basic Cleaning']) await bkCase('same home, other service', s, 'One-Time', '3', '2', '1500-1799 Sq Ft');
    for (const b of ['1', '5']) await bkCase('basic: bedrooms vary', 'Basic Cleaning', 'One-Time', b, '2', '1500-1799 Sq Ft');
    for (const ba of ['1', '4']) await bkCase('basic: bathrooms vary', 'Basic Cleaning', 'One-Time', '3', ba, '1500-1799 Sq Ft');
    for (const sq of ['1000-1249 Sq Ft', '2100-2399 Sq Ft']) await bkCase('move: sq ft vary', 'Move In/Out Clean', 'One-Time', '3', '2', sq);
    await bkCase('move: recurring offered?', 'Move In/Out Clean', 'Every Other Week', '3', '2', '1500-1799 Sq Ft');
    const rf = results.filter((r) => r.company === 'Red Feather Cleaning');
    const varies = (t: string) => new Set(rf.filter((r) => r.test === t).map((r) => r.observed.total_before_tax)).size > 1;
    notes.push(`Red Feather: bedrooms change move-out price: ${varies('move: bedrooms vary')}; bathrooms: ${varies('move: bathrooms vary')}; basic bedrooms: ${varies('basic: bedrooms vary')}; basic bathrooms: ${varies('basic: bathrooms vary')}; sq ft: ${varies('move: sq ft vary')}`);
    });
    await section('Maid 2 Clean', async () => {

    // ---------------------------------------------------------------- 2. Maid 2 Clean KY
    log('\n[2/3] Maid 2 Clean KY');
    await page.goto('https://maidtocleanky.launch27.com/', { waitUntil: 'domcontentloaded' }).catch(() => undefined);
    const oldFeed = await l27Feed(page).catch((e) => ({ services: { status: 0, body: String(e) }, frequencies: { status: 0, body: '' } }));
    notes.push(`Maid 2 Clean: discovery host maidtocleanky.launch27.com feed status ${oldFeed.services.status} (${String(oldFeed.services.body).slice(0, 60).trim()})`);
    await page.goto('https://www.maid2cleanky.com/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const widget = await page.evaluate(() => {
      const w: any = window as any;
      const out: any[] = [];
      if (!w.jQuery || !w.BEDROOM_RATES) return { error: 'price widget not found', out };
      for (const [b, ba] of [[1, 1], [3, 2], [4, 3]]) for (const f of ['r1', 'r3']) {
        w.jQuery('#ui-slider1').slider('value', b);
        w.jQuery('#ui-slider2').slider('value', ba);
        w.jQuery('#' + f).prop('checked', true).trigger('change');
        if (typeof w.updatePrice === 'function') w.updatePrice();
        out.push({ bedrooms: b, bathrooms: ba, frequency: f === 'r1' ? '1 time service' : 'Every 2 weeks', shown: w.jQuery('#total-price').text() });
      }
      return { rates: w.BEDROOM_RATES, perBath: w.PER_BATHROOM, out };
    });
    const wshot = await shot(page, dir, 'maid2clean_homepage_widget');
    for (const o of (widget as any).out || []) {
      rec({ company: 'Maid 2 Clean KY', test: 'home-page price widget', inputs: { bedrooms: String(o.bedrooms), bathrooms: String(o.bathrooms), frequency: o.frequency },
            observed: { shown_per_clean: num(o.shown) }, calculated: null, calcSource: `widget script rates ${JSON.stringify((widget as any).rates)} + $${(widget as any).perBath}/bath`,
            match: '', summaryText: `$${o.shown}/clean`, screenshot: wshot });
    }
    await page.goto('https://www.maid2cleanky.com/booking-page/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    iframe = await page.evaluate(() => [...document.querySelectorAll('iframe')].map((f) => (f as HTMLIFrameElement).src).find((s) => /launch27\.com/.test(s)) || '');
    notes.push(`Maid 2 Clean booking page iframe: ${iframe || 'none found'}`);
    });

    // ---------------------------------------------------------------- 3. Launch27 spot checks
    log('\n[3/3] Launch27 spot checks');
    const targets = [
      { company: 'Super Cleaning Service Louisville', url: 'https://supercleaning.launch27.com/?w_cleaning', key: 'super' as const, biweekly: 'Every 2 Weeks (Save 25%)', one: 'One Time' },
      ...(iframe ? [{ company: 'Maid 2 Clean KY', url: iframe.split('&iframe_id')[0], key: 'm2' as const, biweekly: 'Biweekly', one: 'One Time' }] : []),
    ];
    for (const t of targets) await section(`Launch27 ${t.company}`, async () => {
      await page.goto(t.url, { waitUntil: 'networkidle' }).catch(() => page.goto(t.url, { waitUntil: 'domcontentloaded' }));
      await page.waitForTimeout(2000);
      const feed = await l27Feed(page);
      fs.writeFileSync(path.join(dir, `${t.key}_feed.json`), JSON.stringify(feed, (k, v) => (k === 'icon' || k === 'image' ? undefined : v), 1));
      for (const h of HOMES) {
        const sel = h.l27[t.key];
        const [service, ...others] = sel;
        for (const [label, freq, deep] of [['one-time standard', t.one, false], ['biweekly standard', t.biweekly, false], ['one-time deep', t.one, true]] as const) {
          const panel = await l27Case(page, { service, others, freq, deep });
          const picks: Record<string, string> = {};
          others.filter(Boolean).forEach((o, i) => (picks[`p${i}`] = o));
          const calc = l27Calc(feed, service, picks, freq, deep ? 'Deep Cleaning' : null);
          const base = num((panel.match(/(?:BASE PRICE|SUB-TOTAL) \| \$?([\d.,]+)/) || [])[1]);
          const saving = num((panel.match(/(?:SAVINGS|DISCOUNT) \| \$?([\d.,]+)/) || [])[1]) || 0;
          const tax = num((panel.match(/SALES TAX \| \$?([\d.,]+)/) || [])[1]);
          const total = num((panel.match(/(?:^|\| )TOTAL \| \$?([\d.,]+)/) || [])[1]);
          const recurring = num((panel.match(/Recurring Cleaning Price \| \$?([\d.,]+)/) || [])[1]);
          const pre = base === null ? null : Math.round((base - saving) * 100) / 100;
          const name = `${t.key}_${h.id}_${label.replace(/\W+/g, '_')}`;
          const file = await shot(page, dir, name);
          rec({ company: t.company, test: `${h.id}: ${label}`, inputs: { service, options: others.filter(Boolean).join('; '), frequency: freq, deepExtra: deep },
                observed: { pretax_first_visit: pre, discount: saving, sales_tax: tax, total, recurring_visit: recurring },
                calculated: calc, calcSource: "site's Launch27 feed (fetched in the same session)",
                match: pre !== null && calc !== null ? (Math.abs(pre - calc) < 0.005 ? 'yes' : `NO (diff ${(pre - calc).toFixed(2)})`) : 'not comparable',
                summaryText: panel, screenshot: file });
        }
      }
    });
  } catch (err) {
    notes.push(`ERROR: ${(err as Error).message.split('\n')[0]}`);
    log(`  [error] ${(err as Error).message.split('\n')[0]}`);
  } finally {
    const blocked = session.networkPosts.filter((p) => p.blocked).length;
    notes.push(`Submission guard: ${blocked} booking/lead POSTs blocked; ${session.networkPosts.length} non-GET requests logged`);
    await session.close();
  }
  fs.writeFileSync(path.join(dir, 'results.json'), JSON.stringify({ notes, results }, null, 1));
  const keys = ['company', 'test', 'inputs', 'observed', 'calculated', 'calcSource', 'match', 'summaryText', 'url', 'timestamp', 'screenshot'];
  const esc = (v: unknown) => {
    const s = typeof v === 'object' && v !== null ? JSON.stringify(v) : v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  fs.writeFileSync(path.join(dir, 'results.csv'), '﻿' + [keys.join(','), ...results.map((r: any) => keys.map((k) => esc(r[k])).join(','))].join('\r\n'));
  log(`\n${results.length} observations; ${results.filter((r) => r.match.startsWith('NO')).length} discrepancies`);
  notes.forEach((n) => log('  ' + n));
  log(`Saved: ${dir}`);
  return dir;
}
