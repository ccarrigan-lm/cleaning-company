import { Page } from 'playwright';

/**
 * Launch27 booking forms load their full price table from /v1/booking/services and
 * /v1/booking/frequencies. This reads those feeds from inside the page (the same requests the
 * form makes on load) and expands every combination of every pricing parameter.
 *
 * Price = service base + each pricing parameter (ranged: the chosen range's price; flat: price x
 * quantity), then the frequency's % discount. Deep / move-in-out add-on extras are expanded as
 * one-time only. Works for any Launch27 site, not just Super Cleaning's layout.
 */
export interface L27Row {
  service: string;
  frequency: string;
  bedrooms: string;
  bathrooms: string;
  fullBaths: number | '';
  halfBaths: number | '';
  sqft: string;
  /** Every pricing parameter value, as "Name=Value; Name=Value". */
  options: string;
  addOn: string;
  firstVisitPreTax: number;
  recurringVisitPreTax: number | null;
}

const MAX_FLAT_QTY = 6;
/** Only these parameters are expanded; any other counter (kitchens, laundry loads, stories...) stays at its minimum. */
const SIZE_PARAM = /bed|bath|sq|feet|footage|size|area/i;

export async function harvestLaunch27(page: Page, formUrl: string, log = console.log, maxCombos = 80000): Promise<{ rows: L27Row[]; raw: any; extras: { service: string; name: string; price: number; quantityBased: boolean }[] }> {
  await page.goto(formUrl, { waitUntil: 'networkidle' }).catch(() => page.goto(formUrl, { waitUntil: 'domcontentloaded' }));
  const raw = await page.evaluate(async () => {
    const get = (u: string) => fetch(u, { headers: { Accept: 'application/json' } }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    let services = await get('/v1/booking/services?location_id=1&mode=tags');
    if (!services?.services?.length) services = await get('/v1/booking/services?mode=tags');
    let frequencies = await get('/v1/booking/frequencies?location_id=1');
    if (!Array.isArray(frequencies) || !frequencies.length) frequencies = await get('/v1/booking/frequencies');
    return { services, frequencies };
  });
  if (!raw.services?.services?.length) throw new Error('Launch27 price feed not found on this page');
  const freqs: any[] = Array.isArray(raw.frequencies) && raw.frequencies.length ? raw.frequencies : [{ name: 'One Time', percent: 0, interval: 'o' }];

  const rows: L27Row[] = [];
  const extras: { service: string; name: string; price: number; quantityBased: boolean }[] = [];
  const r2 = (n: number) => Math.round(n * 100) / 100;
  for (const svc of raw.services.services) {
    for (const e of svc.extras ?? []) extras.push({ service: svc.name, name: e.name, price: Number(e.price) || 0, quantityBased: !!e.quantity_based });
    if (svc.hourly) continue;
    // Each pricing parameter becomes one dimension: a list of (label, price) choices.
    const dims: { name: string; choices: { label: string; value: number | string; price: number }[] }[] = [];
    for (const p of svc.pricing_parameters ?? []) {
      if (p.type === 'ranged') {
        if (!SIZE_PARAM.test(p.name)) {
          const r0 = (p.ranges ?? [])[0];
          if (r0) dims.push({ name: p.name, choices: [{ label: r0.label, value: r0.label, price: Number(r0.price) || 0 }] });
          continue;
        }
        dims.push({ name: p.name, choices: (p.ranges ?? []).map((r: any) => ({ label: r.label, value: r.label, price: Number(r.price) || 0 })) });
      } else {
        const lo = Number(p.quantity_minimum ?? 0);
        const hi = SIZE_PARAM.test(p.name) ? Math.min(Number(p.quantity_maximum ?? lo), lo + MAX_FLAT_QTY) : lo;
        const ch = [];
        for (let q = lo; q <= hi; q++) ch.push({ label: String(q), value: q, price: q * (Number(p.price) || 0) });
        dims.push({ name: p.name, choices: ch });
      }
    }
    const addOns = [{ name: '', price: 0 }, ...(svc.extras ?? []).filter((e: any) => !e.quantity_based && /deep|move/i.test(e.name)).map((e: any) => ({ name: e.name, price: Number(e.price) || 0 }))];
    const svcBeds = (svc.name.match(/(\d+)\s*(bed|br|bd)/i) || [])[1] ?? (/studio/i.test(svc.name) ? '0' : '');
    const total = dims.reduce((n, d) => n * Math.max(d.choices.length, 1), 1);
    const svcStart = rows.length;
    svcLoop: for (const f of freqs) {
      const m = 1 - (Number(f.percent) || 0) / 100;
      for (let c = 0; c < total; c++) {
        let rem = c;
        const pick = dims.map((d) => {
          const i = rem % d.choices.length;
          rem = Math.floor(rem / d.choices.length);
          return d.choices[i];
        });
        const base = (Number(svc.price) || 0) + pick.reduce((s, p) => s + p.price, 0);
        const find = (re: RegExp, not?: RegExp) => {
          const i = dims.findIndex((d) => re.test(d.name) && !(not && not.test(d.name)));
          return i < 0 ? undefined : pick[i];
        };
        const full = find(/bath/i, /half/i), half = find(/half/i), bed = find(/bed/i), sq = find(/sq|feet|footage|size/i);
        const fb = full ? Number(full.value) : '', hb = half ? Number(half.value) : '';
        const baths = full ? String(Number(full.value) + (half ? 0.5 * Number(half.value) : 0)) : '';
        for (const a of addOns) {
          if (a.name && f.percent) continue; // deep / move only harvested as one-time
          rows.push({
            service: svc.name,
            frequency: f.name,
            bedrooms: bed ? String(bed.value) : svcBeds,
            bathrooms: baths,
            fullBaths: fb,
            halfBaths: hb,
            sqft: sq ? String(sq.label) : '',
            options: dims.map((d, i) => `${d.name}=${pick[i].label}`).join('; '),
            addOn: a.name,
            firstVisitPreTax: r2((base + a.price) * (f.exclude_first ? 1 : m)),
            recurringVisitPreTax: f.interval === 'o' || !f.percent ? (f.interval === 'o' ? null : r2(base)) : r2(base * m),
          });
          if (rows.length >= maxCombos) {
            log(`  [warn] stopped at ${maxCombos} combinations`);
            return { rows, raw, extras };
          }
          if (rows.length - svcStart >= 15000) break svcLoop;
        }
      }
    }
  }
  log(`  ${rows.length} combinations expanded from the price feed (${raw.services.services.length} services, ${freqs.length} frequencies)`);
  return { rows, raw, extras };
}
