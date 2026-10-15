import fs from 'fs';
import path from 'path';
import { Page } from 'playwright';
import { launch, NetworkLogEntry } from '../capture/browser';
import { Settings } from '../config';

/**
 * Louisville-only live validation (npm run validate:louisville).
 *
 * Reads prices from the live booking forms only. It types the pricing ZIP and changes the
 * price selectors; it never fills contact, address, date or payment fields and never
 * clicks a booking/submit button (the network guard also blocks booking POSTs).
 *
 * Every planned check has an id and ends with one status:
 *   passed       price observed by THIS run and equal to the expectation
 *   failed       price observed and different from the expectation (never hidden by a count of 0)
 *   error        the check could not be completed (exception); message + screenshot kept
 *   inconclusive the page was reached but the price or the selection could not be confirmed
 *   not_run      not selected (--only / --rerun) or its section stopped before reaching it
 *   observation  discovery-only items (feed host status, iframe, homepage widget): no price comparison
 *
 * Expectations:
 *   Launch27      = price calculated from the site's own feed fetched in the same session (primary);
 *                   the 14 Oct by-hand observation is shown alongside (secondary, comparison only).
 *   BookingKoala  = 14 Oct by-hand observation (research/validation/louisville_expected.json); there is
 *                   no feed to calculate from. By-hand values never replace an automated observation.
 *
 * Re-run subsets:  --only rf,l27-super-typical      (ids or id prefixes, comma separated)
 *                  --rerun output/validation/<stamp> (re-runs every check in that run whose status != passed/observation)
 *
 * Output: output/validation/<stamp>/{results.json, results.csv, summary.json, network_requests.json, screenshots/}
 */

type Status = 'passed' | 'failed' | 'error' | 'inconclusive' | 'not_run' | 'observation';

interface Check {
  id: string;
  company: string;
  group: string;
  kind: 'price' | 'discovery';
  test: string;
  inputs: Record<string, string | boolean>;
  status: Status;
  reason: string;
  observed: Record<string, number | string | null | boolean>;
  expected: number | null;
  expectedSource: string;
  byhand: number | null;
  difference: number | null;
  summaryText: string;
  url: string;
  timestamp: string;
  screenshot: string;
  settle: Record<string, number | boolean>;
}

const HOMES = [
  { id: 'small', l27: { super: ['One Bedroom Home', '1-999 sq ft', '1 Bathroom', '0 Half-bathrooms'], m2: ['One Bedroom Home', '1 Bathroom'] } },
  { id: 'typical', l27: { super: ['Three Bedroom Home', '1500-1999 sq ft', '2 Bathrooms', '0 Half-bathrooms'], m2: ['Three Bedroom Home', '2 Bathrooms', 'Over 1500 sq.ft'] } },
  { id: 'larger', l27: { super: ['Four Bedroom Home', '3000-3499 sq ft', '3 Bathrooms', '0 Half-bathrooms'], m2: ['Four Bedroom Home', '3 Bathrooms', 'Over 3000 sq.ft'] } },
] as const;
const L27_CASES = [['one', 'one-time standard', false], ['biweekly', 'biweekly standard', false], ['deep', 'one-time deep', true]] as const;

const RF_CHECKS: [string, string, string, string, string, string, string][] = [
  ...['0', '1', '2', '3', '4', '5'].map((b) => [`rf-move-bd${b}`, 'move: bedrooms vary', 'Move In/Out Clean', 'One-Time', b, '2', '1500-1799 Sq Ft'] as [string, string, string, string, string, string, string]),
  ...['1', '1.5', '2.5', '3', '4'].map((ba) => [`rf-move-ba${ba}`, 'move: bathrooms vary', 'Move In/Out Clean', 'One-Time', '3', ba, '1500-1799 Sq Ft'] as [string, string, string, string, string, string, string]),
  ['rf-same-deep', 'same home, other service', 'Deep Clean', 'One-Time', '3', '2', '1500-1799 Sq Ft'],
  ['rf-same-basic', 'same home, other service', 'Basic Cleaning', 'One-Time', '3', '2', '1500-1799 Sq Ft'],
  ...['1', '5'].map((b) => [`rf-basic-bd${b}`, 'basic: bedrooms vary', 'Basic Cleaning', 'One-Time', b, '2', '1500-1799 Sq Ft'] as [string, string, string, string, string, string, string]),
  ...['1', '4'].map((ba) => [`rf-basic-ba${ba}`, 'basic: bathrooms vary', 'Basic Cleaning', 'One-Time', '3', ba, '1500-1799 Sq Ft'] as [string, string, string, string, string, string, string]),
  ['rf-move-sq1000', 'move: sq ft vary', 'Move In/Out Clean', 'One-Time', '3', '2', '1000-1249 Sq Ft'],
  ['rf-move-sq2100', 'move: sq ft vary', 'Move In/Out Clean', 'One-Time', '3', '2', '2100-2399 Sq Ft'],
  ['rf-move-eow', 'move: recurring offered?', 'Move In/Out Clean', 'Every Other Week', '3', '2', '1500-1799 Sq Ft'],
];

// Non-GET requests these pages are known to make (14-15 Oct built-in-browser network capture). Anything else is "unexpected - review".
const EXPECTED_NON_GET: [RegExp, string][] = [
  [/bookingkoala\.com\/cdn-cgi\/rum$/, 'Cloudflare analytics beacon (BookingKoala page)'],
  [/bookingkoala\.com\/api\/v4\/form-custom-fields$/, 'BookingKoala form configuration read'],
  [/bookingkoala\.com\/api\/v7\/addons\/search$/, 'BookingKoala add-on list read'],
  [/bookingkoala\.com\/leads\/v1\/pages\/popups$/, 'BookingKoala popup configuration read (explicitly not blocked)'],
  [/launch27\.com\/v1\/booking\/estimate_price$/, 'Launch27 price estimate for the current selections'],
  [/launch27\.com\/v1\/booking\/spots$/, 'Launch27 available time-slot lookup'],
  // Third-party scripts the booking pages load on their own (identified in run 2026-10-15-14-08-17; nothing typed into them):
  [/^https:\/\/r\.stripe\.com\/b$/, 'THIRD-PARTY: Stripe.js telemetry beacon (payment widget embedded in the form; no card data entered)'],
  [/^https:\/\/m\.stripe\.com\/6$/, 'THIRD-PARTY: Stripe fraud-detection device fingerprint'],
  [/^https:\/\/merchant-ui-api\.stripe\.com\/elements\/wallet-config$/, 'THIRD-PARTY: Stripe wallet (Apple/Google Pay) configuration'],
  [/^https:\/\/api\.hcaptcha\.com\/(checksiteconfig|getcaptcha\/[\w-]+)$/, 'THIRD-PARTY: hCaptcha widget load / challenge fetch (not solved)'],
  [/^https:\/\/(analytics\.google\.com\/g\/collect|stats\.g\.doubleclick\.net\/g\/collect)$/, 'THIRD-PARTY: Google Analytics / DoubleClick'],
  [/^https:\/\/sessions\.bugsnag\.com\/$/, 'THIRD-PARTY: Bugsnag error-reporting session'],
  [/^https:\/\/(bootstrap\.driftapi\.com\/widget_bootstrap(\/ping\/v2)?|metrics\.api\.drift\.com\/monitoring\/metrics\/widget\/init\/v3)$/, 'THIRD-PARTY: Drift chat widget'],
];

/** Money after a label, tolerating icon-font currency glyphs (e.g. U+F155) or "$" between label and digits. */
const moneyAfter = (s: string, label: RegExp): number | null => {
  const m = s.match(new RegExp(label.source + String.raw`\s*\|?\s*[^\d\s|-]{0,3}\s*(-?[\d,]+(?:\.\d+)?)`));
  return m ? parseFloat(m[1].replace(/,/g, '')) : null;
};
const num = (s: string | undefined | null) => {
  const m = (s || '').replace(/,/g, '').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : null;
};

async function settle(page: Page, read: () => Promise<string>, ready: (s: string) => boolean, quietMs = 1500, maxMs = 15000) {
  const t0 = Date.now();
  let last = await read();
  let since = Date.now();
  let readyAt = ready(last) ? Date.now() : 0;
  while (Date.now() - t0 < maxMs) {
    await page.waitForTimeout(250);
    const n = await read();
    if (n !== last) {
      last = n;
      since = Date.now();
    }
    if (!readyAt && ready(last)) readyAt = Date.now();
    if (readyAt && Date.now() - since > quietMs) break;
  }
  return { text: last, reflected: !!readyAt, waitedMs: Date.now() - t0, quietMs: Date.now() - since };
}

// ------------------------------------------------------------------------------------------- Launch27 helpers
async function l27Feed(page: Page) {
  return page.evaluate(async () => {
    const get = (u: string) => fetch(u, { headers: { Accept: 'application/json' } }).then(async (r) => ({ status: r.status, body: r.ok ? await r.json() : await r.text() }));
    return { services: await get('/v1/booking/services?location_id=1&mode=tags'), frequencies: await get('/v1/booking/frequencies?location_id=1') };
  });
}

function l27Calc(feed: any, service: string, picks: string[], freqName: string, addOnPrefix: string | null) {
  const svc = feed.services.body.services.find((s: any) => s.name === service);
  if (!svc) return null;
  let p = Number(svc.price);
  for (const prm of svc.pricing_parameters || []) {
    if (prm.type === 'ranged') {
      const r = prm.ranges.find((x: any) => picks.includes(x.label));
      p += r ? Number(r.price) : 0;
    } else {
      const want = picks.find((v) => new RegExp(prm.name.replace(/-?s$/i, ''), 'i').test(v) && /^\d/.test(v));
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

/** Texts currently selected in the visible selects (fresh lookup every time). */
async function l27Selected(page: Page): Promise<string[]> {
  return page.evaluate(() => ([...document.querySelectorAll('select')] as HTMLSelectElement[])
    .filter((s) => s.offsetParent).map((s) => s.options[s.selectedIndex]?.text.trim() || ''));
}

/**
 * Choose an option by its exact text. Launch27 rebuilds every select when the service changes, so the
 * element is looked up fresh (by the option it offers) and we never keep a handle or marker on it
 * (the 15 Oct run timed out waiting for a marked select that the re-render had removed).
 */
async function l27Select(page: Page, optionText: string) {
  const lit = JSON.stringify(optionText);
  const sel = page.locator(`xpath=//select[option[normalize-space(.)=${lit}]]`).filter({ visible: true }).first();
  await sel.waitFor({ state: 'visible', timeout: 15000 });
  await sel.selectOption({ label: optionText });
  await page.waitForFunction((t) => ([...document.querySelectorAll('select')] as HTMLSelectElement[])
    .some((s) => s.offsetParent && s.options[s.selectedIndex]?.text.trim() === t), optionText, { timeout: 15000 });
}

async function shot(page: Page, dir: string, name: string) {
  const file = path.join(dir, 'screenshots', `${name}.png`);
  await page.screenshot({ path: file, fullPage: false }).catch(() => undefined);
  return path.relative(path.dirname(dir), file);
}

// ------------------------------------------------------------------------------------------- main
export async function validateLouisville(settings: Settings, outRoot: string, log = console.log, opts: { only?: string; rerun?: string } = {}) {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const dir = path.join(outRoot, 'validation', stamp);
  fs.mkdirSync(path.join(dir, 'screenshots'), { recursive: true });
  const expectedFile = path.resolve(__dirname, '..', '..', 'research', 'validation', 'louisville_expected.json');
  const expected: Record<string, any> = fs.existsSync(expectedFile) ? JSON.parse(fs.readFileSync(expectedFile, 'utf8')).checks : {};

  // ---- plan: every check that exists, with status not_run until it runs
  const checks = new Map<string, Check>();
  const plan = (c: Partial<Check> & Pick<Check, 'id' | 'company' | 'group' | 'kind' | 'test' | 'inputs'>) =>
    checks.set(c.id, { status: 'not_run', reason: 'not reached', observed: {}, expected: null, expectedSource: '', byhand: null, difference: null,
                       summaryText: '', url: '', timestamp: '', screenshot: '', settle: {}, ...c });
  for (const [id, test, service, frequency, bedrooms, bathrooms, sqft] of RF_CHECKS)
    plan({ id, company: 'Red Feather Cleaning', group: 'rf', kind: 'price', test, inputs: { service, frequency, bedrooms, bathrooms, sqft, zip: '40217' } });
  plan({ id: 'm2-disc-oldhost', company: 'Maid 2 Clean KY', group: 'm2-disc', kind: 'discovery', test: 'discovery Launch27 host feed status', inputs: { url: 'https://maidtocleanky.launch27.com/' } });
  plan({ id: 'm2-disc-iframe', company: 'Maid 2 Clean KY', group: 'm2-disc', kind: 'discovery', test: 'booking-page iframe host', inputs: { url: 'https://www.maid2cleanky.com/booking-page/' } });
  for (const [b, ba] of [[1, 1], [3, 2], [4, 3]]) for (const f of ['one', 'biweekly'])
    plan({ id: `m2-widget-${b}-${ba}-${f}`, company: 'Maid 2 Clean KY', group: 'm2-disc', kind: 'discovery', test: 'home-page price widget (not the booking form)', inputs: { bedrooms: String(b), bathrooms: String(ba), frequency: f } });
  for (const key of ['super', 'm2'] as const) for (const h of HOMES) for (const [c, label, deep] of L27_CASES)
    plan({ id: `l27-${key}-${h.id}-${c}`, company: key === 'super' ? 'Super Cleaning Service Louisville' : 'Maid 2 Clean KY', group: `l27-${key}`, kind: 'price',
           test: `${h.id}: ${label}`, inputs: { selections: h.l27[key].join('; '), case: c, deepExtra: deep } });

  // ---- selection
  let selected = new Set(checks.keys());
  if (opts.rerun) {
    const prev = JSON.parse(fs.readFileSync(path.join(opts.rerun, 'summary.json'), 'utf8'));
    selected = new Set((prev.checks as { id: string; status: Status }[]).filter((c) => !['passed', 'observation'].includes(c.status)).map((c) => c.id));
  }
  if (opts.only) {
    const pre = opts.only.split(',').map((s) => s.trim()).filter(Boolean);
    selected = new Set([...selected].filter((id) => pre.some((p) => id === p || id.startsWith(p))));
  }
  for (const [id, c] of checks) if (!selected.has(id)) c.reason = 'not selected for this run';
  const want = (id: string) => selected.has(id);
  const wantAny = (prefix: string) => [...selected].some((id) => id.startsWith(prefix));
  log(`Planned checks: ${checks.size}; selected for this run: ${selected.size}`);

  const notes: string[] = [];
  const session = await launch(settings);
  const page = session.page;
  const finish = (c: Check, upd: Partial<Check>) => Object.assign(c, { url: page.url(), timestamp: new Date().toISOString() }, upd);
  const section = async (name: string, ids: string[], fn: () => Promise<void>) => {
    try {
      await fn();
    } catch (err) {
      const msg = (err as Error).message.split('\n')[0];
      notes.push(`ERROR in ${name}: ${msg}`);
      log(`  [error] ${name}: ${msg}`);
      for (const id of ids) {
        const c = checks.get(id)!;
        if (c.status === 'not_run' && want(id)) c.reason = `section stopped before this check: ${msg}`;
      }
    }
  };

  try {
    // ---------------------------------------------------------------- 1. Red Feather (BookingKoala)
    const rfIds = RF_CHECKS.map((r) => r[0]);
    if (rfIds.some(want)) await section('Red Feather', rfIds, async () => {
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
      for (const [id, test, service, freq, bed, bath, sq] of RF_CHECKS) {
        if (!want(id)) continue;
        const c = checks.get(id)!;
        try {
          await bkSel('Services', service);
          await page.waitForTimeout(500);
          const radio = page.locator('input[name=frequency]').locator('xpath=..').filter({ hasText: freq }).locator('input[name=frequency]').first();
          if (await radio.count()) await radio.check({ force: true }).catch(() => undefined);
          await bkSel('Bedrooms', bed);
          await bkSel('Bathrooms', bath);
          await bkSel('Sq Ft', sq);
          // ready = the summary shows every requested selection (frequency excepted: the move-out recurring check expects it NOT to apply)
          const shows = (s: string) => s.includes(`Service ${service} `) && s.includes(`Bedrooms ${bed} `) && s.includes(`Bathrooms ${bath} `) && s.includes(`Sq Ft ${sq}`) && /Total Before Tax/.test(s);
          const st = await settle(page, bkSummary, shows);
          const s = st.text;
          await page.locator('#booking-summary').scrollIntoViewIfNeeded().catch(() => undefined);
          const file = await shot(page, dir, id);
          const pre = moneyAfter(s, /Total Before Tax/);
          const tot = moneyAfter(s, /TOTAL/);
          const freqShown = (s.match(/Frequency (.*?) Bedrooms/) || [])[1] || null;
          const exp = expected[id] || {};
          const byhand = exp.byhand_total_before_tax ?? null;
          let status: Status;
          let reason: string;
          if (!st.reflected) [status, reason] = ['inconclusive', 'Booking Summary never showed all requested selections'];
          else if (pre === null) [status, reason] = ['inconclusive', 'price not found in the Booking Summary text'];
          else if (byhand === null) [status, reason] = ['inconclusive', 'no comparison evidence for this check'];
          else if (Math.abs(pre - byhand) >= 0.005) [status, reason] = ['failed', `observed ${pre} vs 14 Oct by-hand ${byhand}`];
          else if (id === 'rf-move-eow' && freqShown !== exp.byhand_frequency_shown) [status, reason] = ['failed', `frequency shown ${freqShown} vs by-hand ${exp.byhand_frequency_shown}`];
          else [status, reason] = ['passed', id === 'rf-move-eow' ? `price matches; frequency shown "${freqShown}" (recurring not applied, as on 14 Oct)` : 'price matches 14 Oct by-hand observation'];
          finish(c, { status, reason, summaryText: s, screenshot: file, expected: byhand, byhand, expectedSource: 'by-hand built-in browser 14 Oct (no BookingKoala feed)',
                      difference: pre !== null && byhand !== null ? Math.round((pre - byhand) * 100) / 100 : null,
                      observed: { service_shown: (s.match(/Service (.*?) Frequency/) || [])[1] || null, frequency_shown: freqShown, total_before_tax: pre, total: tot },
                      settle: { reflected: st.reflected, waitedMs: st.waitedMs, quietMs: st.quietMs } });
        } catch (err) {
          finish(c, { status: 'error', reason: (err as Error).message.split('\n')[0], screenshot: await shot(page, dir, `${id}_error`) });
        }
        log(`  ${c.status.padEnd(12)} ${id} ${c.observed.total_before_tax ?? ''} ${c.reason}`);
      }
      // structure findings only from checks that passed in THIS run
      const vary = (prefix: string) => {
        const g = [...checks.values()].filter((c) => c.id.startsWith(prefix) && want(c.id));
        if (!g.length) return 'not run';
        if (g.some((c) => c.status !== 'passed')) return `inconclusive (${g.filter((c) => c.status !== 'passed').length} of ${g.length} checks not passed)`;
        return String(new Set(g.map((c) => c.observed.total_before_tax)).size > 1);
      };
      notes.push(`Red Feather (from passed checks only): bedrooms change move-out price: ${vary('rf-move-bd')}; bathrooms: ${vary('rf-move-ba')}; basic bedrooms: ${vary('rf-basic-bd')}; basic bathrooms: ${vary('rf-basic-ba')}; sq ft: ${vary('rf-move-sq')}`);
    });

    // ---------------------------------------------------------------- 2. Maid 2 Clean discovery (observations, not price checks)
    let iframe = '';
    if (wantAny('m2-') || wantAny('l27-m2')) await section('Maid 2 Clean discovery', [...checks.keys()].filter((k) => k.startsWith('m2-')), async () => {
      log('\n[2/3] Maid 2 Clean KY (discovery observations)');
      if (want('m2-disc-oldhost')) {
        await page.goto('https://maidtocleanky.launch27.com/', { waitUntil: 'domcontentloaded' }).catch(() => undefined);
        const oldFeed = await l27Feed(page).catch((e) => ({ services: { status: 0, body: String(e) }, frequencies: { status: 0, body: '' } }));
        finish(checks.get('m2-disc-oldhost')!, { status: 'observation', reason: `feed status ${oldFeed.services.status} (${String(oldFeed.services.body).slice(0, 60).trim()})`, observed: { feed_status: oldFeed.services.status } });
      }
      if ([...selected].some((id) => id.startsWith('m2-widget'))) {
        await page.goto('https://www.maid2cleanky.com/', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2500);
        const widget: any = await page.evaluate(() => {
          const w: any = window as any;
          const out: any[] = [];
          if (!w.jQuery || !w.BEDROOM_RATES) return { error: 'price widget not found', out };
          for (const [b, ba] of [[1, 1], [3, 2], [4, 3]]) for (const f of ['r1', 'r3']) {
            w.jQuery('#ui-slider1').slider('value', b);
            w.jQuery('#ui-slider2').slider('value', ba);
            w.jQuery('#' + f).prop('checked', true).trigger('change');
            if (typeof w.updatePrice === 'function') w.updatePrice();
            out.push({ b, ba, f: f === 'r1' ? 'one' : 'biweekly', shown: w.jQuery('#total-price').text() });
          }
          return { rates: w.BEDROOM_RATES, perBath: w.PER_BATHROOM, out };
        });
        const wshot = await shot(page, dir, 'm2-widget');
        for (const o of widget.out || []) {
          const c = checks.get(`m2-widget-${o.b}-${o.ba}-${o.f}`);
          if (c && want(c.id)) finish(c, { status: 'observation', reason: `homepage widget shows $${o.shown}/clean (widget formula ${JSON.stringify(widget.rates)} + $${widget.perBath}/bath; differs from the booking form by design - not a price check)`,
                                           observed: { shown_per_clean: num(o.shown) }, screenshot: wshot });
        }
      }
      await page.goto('https://www.maid2cleanky.com/booking-page/', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);
      iframe = await page.evaluate(() => [...document.querySelectorAll('iframe')].map((f) => (f as HTMLIFrameElement).src).find((s) => /launch27\.com/.test(s)) || '');
      if (want('m2-disc-iframe')) finish(checks.get('m2-disc-iframe')!, { status: 'observation', reason: iframe ? `iframe ${iframe}` : 'no Launch27 iframe found', observed: { iframe } });
    });

    // ---------------------------------------------------------------- 3. Launch27 spot checks (each check isolated)
    log('\n[3/3] Launch27 spot checks');
    const targets = [
      { company: 'Super Cleaning Service Louisville', url: 'https://supercleaning.launch27.com/?w_cleaning', key: 'super' as const, biweekly: 'Every 2 Weeks (Save 25%)', one: 'One Time' },
      { company: 'Maid 2 Clean KY', url: iframe ? iframe.split('&iframe_id')[0] : 'https://smilesaremaid.launch27.com/?w_cleaning', key: 'm2' as const, biweekly: 'Biweekly', one: 'One Time' },
    ];
    for (const t of targets) {
      const ids = [...checks.keys()].filter((k) => k.startsWith(`l27-${t.key}-`));
      if (!ids.some(want)) continue;
      await section(`Launch27 ${t.company}`, ids, async () => {
        await page.goto(t.url, { waitUntil: 'networkidle' }).catch(() => page.goto(t.url, { waitUntil: 'domcontentloaded' }));
        await page.waitForTimeout(2000);
        const feed = await l27Feed(page);
        fs.writeFileSync(path.join(dir, `${t.key}_feed.json`), JSON.stringify(feed, (k, v) => (k === 'icon' || k === 'image' ? undefined : v), 1));
        let lastEstimate = 0;
        let inflight = 0;
        const isEst = (u: string) => /\/v1\/booking\/estimate_price$/.test(u.split('?')[0]);
        page.on('request', (r) => { if (isEst(r.url())) inflight++; });
        page.on('requestfinished', (r) => { if (isEst(r.url())) { inflight = Math.max(0, inflight - 1); lastEstimate = Date.now(); } });
        page.on('requestfailed', (r) => { if (isEst(r.url())) inflight = Math.max(0, inflight - 1); });
        // settled = no estimate in flight AND (an estimate finished after our last change, OR our change triggered none:
        // the selections already equalled the form state - accepted only after 4 s with an earlier estimate on this page)
        for (const h of HOMES) for (const [cs, label, deep] of L27_CASES) {
          const id = `l27-${t.key}-${h.id}-${cs}`;
          if (!want(id)) continue;
          const c = checks.get(id)!;
          const [service, ...others] = h.l27[t.key] as readonly string[];
          const freq = cs === 'biweekly' ? t.biweekly : t.one;
          try {
            const changedAt = Date.now();
            await l27Select(page, service);
            for (const o of others) await l27Select(page, o);
            await page.locator('.frequency-option', { hasText: freq }).first().click({ timeout: 15000 });
            const deepEl = page.locator('.extra-option').filter({ hasText: /^\s*Deep Cleaning/ }).first();
            await deepEl.waitFor({ state: 'visible', timeout: 15000 });
            const active = await deepEl.evaluate((e) => /active|selected|checked/.test(e.className + ' ' + (e.parentElement?.className || '')), undefined, { timeout: 10000 });
            if (active !== deep) await deepEl.click({ timeout: 10000 });
            const want4 = [service, ...others];
            const st = await settle(page, () => l27Panel(page), () => inflight === 0 && (lastEstimate > changedAt || (lastEstimate > 0 && Date.now() - changedAt > 4000)), 2000);
            const shownSel = await l27Selected(page);
            const selOk = want4.every((w) => shownSel.includes(w));
            const panel = st.text;
            const base = moneyAfter(panel, /(?:BASE PRICE|SUB-TOTAL)/);
            const saving = moneyAfter(panel, /(?:SAVINGS|DISCOUNT)/) || 0;
            const tax = moneyAfter(panel, /SALES TAX/);
            const total = moneyAfter(panel, /(?:^|\| )TOTAL/);
            const recurring = moneyAfter(panel, /Recurring Cleaning Price/);
            const pre = base === null ? null : Math.round((base - saving) * 100) / 100;
            const calc = l27Calc(feed, service, others, freq, deep ? 'Deep Cleaning' : null);
            const byhand = expected[id]?.byhand_pretax_first_visit ?? null;
            let status: Status;
            let reason: string;
            if (!selOk) [status, reason] = ['inconclusive', `selects show ${JSON.stringify(shownSel)} not ${JSON.stringify(want4)}`];
            else if (!st.reflected) [status, reason] = ['inconclusive', 'price estimate still pending / never received after the last change'];
            else if (pre === null || calc === null) [status, reason] = ['inconclusive', pre === null ? 'price not found in panel' : 'feed calculation unavailable'];
            else if (Math.abs(pre - calc) >= 0.005) [status, reason] = ['failed', `observed ${pre} vs feed calc ${calc}`];
            else [status, reason] = ['passed', `observed = feed calc${byhand !== null ? (Math.abs(pre - byhand) < 0.005 ? '; = 14 Oct by-hand' : `; differs from 14 Oct by-hand ${byhand}`) : ''}`];
            finish(c, { status, reason, summaryText: panel, screenshot: await shot(page, dir, id), expected: calc, expectedSource: "site's Launch27 feed (same session)", byhand,
                        difference: pre !== null && calc !== null ? Math.round((pre - calc) * 100) / 100 : null,
                        observed: { pretax_first_visit: pre, discount: saving, sales_tax: tax, total, recurring_visit: recurring, selects_shown: shownSel.join('; ') },
                        settle: { reflected: st.reflected, waitedMs: st.waitedMs, quietMs: st.quietMs } });
          } catch (err) {
            finish(c, { status: 'error', reason: (err as Error).message.split('\n')[0], screenshot: await shot(page, dir, `${id}_error`) });
          }
          log(`  ${c.status.padEnd(12)} ${id} ${c.observed.pretax_first_visit ?? ''} ${c.reason}`);
        }
      });
    }
  } catch (err) {
    notes.push(`ERROR: ${(err as Error).message.split('\n')[0]}`);
    log(`  [error] ${(err as Error).message.split('\n')[0]}`);
  } finally {
    await session.close();
  }

  // ---- network log (every non-GET, classified)
  const net = (session.networkPosts as NetworkLogEntry[]).map((n) => {
    const hit = EXPECTED_NON_GET.find(([re]) => re.test(n.url));
    return { ...n, classification: n.blocked ? 'BLOCKED by guard' : hit ? (hit[1].startsWith('THIRD-PARTY') ? hit[1] : `expected: ${hit[1]}`) : 'UNEXPECTED - review' };
  });
  fs.writeFileSync(path.join(dir, 'network_requests.json'), JSON.stringify(net, null, 1));
  const unexpected = net.filter((n) => n.classification.startsWith('UNEXPECTED'));
  const third = net.filter((n) => n.classification.startsWith('THIRD-PARTY'));
  notes.push(`Network: ${net.length} non-GET requests logged (network_requests.json): ${net.length - third.length - unexpected.length - net.filter((n) => n.blocked).length} expected first-party, ${third.length} known third-party scripts, ${net.filter((n) => n.blocked).length} blocked, ${unexpected.length} UNEXPECTED (review)`);

  // ---- outputs
  const all = [...checks.values()];
  const count = (pred: (c: Check) => boolean) => all.filter(pred).length;
  const price = all.filter((c) => c.kind === 'price');
  const summary = {
    run: stamp, selection: opts.rerun ? `rerun of ${opts.rerun}` : opts.only ? `--only ${opts.only}` : 'all',
    price_checks: { planned: price.length, selected: price.filter((c) => selected.has(c.id)).length,
                    completed: count((c) => c.kind === 'price' && ['passed', 'failed', 'inconclusive'].includes(c.status)),
                    passed: count((c) => c.kind === 'price' && c.status === 'passed'), failed: count((c) => c.kind === 'price' && c.status === 'failed'),
                    inconclusive: count((c) => c.kind === 'price' && c.status === 'inconclusive'), error: count((c) => c.kind === 'price' && c.status === 'error'),
                    not_run: count((c) => c.kind === 'price' && c.status === 'not_run') },
    discovery_observations: { planned: all.length - price.length, recorded: count((c) => c.status === 'observation') },
    network: { non_get: net.length, blocked: net.filter((n) => n.blocked).length, known_third_party: third.length, unexpected: unexpected.length },
    notes,
    checks: all.map((c) => ({ id: c.id, kind: c.kind, status: c.status, reason: c.reason })),
  };
  fs.writeFileSync(path.join(dir, 'summary.json'), JSON.stringify(summary, null, 1));
  fs.writeFileSync(path.join(dir, 'results.json'), JSON.stringify({ notes, results: all }, null, 1));
  const keys: (keyof Check)[] = ['id', 'kind', 'status', 'reason', 'company', 'test', 'inputs', 'observed', 'expected', 'expectedSource', 'byhand', 'difference', 'settle', 'summaryText', 'url', 'timestamp', 'screenshot'];
  const esc = (v: unknown) => {
    const s = typeof v === 'object' && v !== null ? JSON.stringify(v) : v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  fs.writeFileSync(path.join(dir, 'results.csv'), '﻿' + [keys.join(','), ...all.map((r) => keys.map((k) => esc(r[k])).join(','))].join('\r\n'));
  const p = summary.price_checks;
  log(`\nPrice checks: planned ${p.planned}, selected ${p.selected}, completed ${p.completed} -> passed ${p.passed}, FAILED ${p.failed}, inconclusive ${p.inconclusive}, error ${p.error}, not run ${p.not_run}`);
  log(`Discovery observations: ${summary.discovery_observations.recorded} of ${summary.discovery_observations.planned}`);
  for (const c of all.filter((x) => ['failed', 'error', 'inconclusive'].includes(x.status))) log(`  ${c.status.toUpperCase()} ${c.id}: ${c.reason}`);
  notes.forEach((n) => log('  ' + n));
  log(`Saved: ${dir}`);
  log(`Re-run anything not passed: npm run validate:louisville -- --rerun ${dir}`);
  return dir;
}
