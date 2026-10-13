import { Page } from 'playwright';

/**
 * Launch27 booking forms (Super Cleaning Service) load their full price table from
 * /v1/booking/services and /v1/booking/frequencies. This reads those feeds from inside the
 * page (same requests the form makes on load) and expands every combination.
 * Price = service base (bedrooms) + sq ft range + per full bath + per half bath, then % off by frequency.
 */
export interface L27Row {
  service: string;
  frequency: string;
  sqft: string;
  fullBaths: number;
  halfBaths: number;
  addOn: string;
  firstVisitPreTax: number;
  recurringVisitPreTax: number | null;
}

export async function harvestLaunch27(page: Page, formUrl: string, log = console.log): Promise<{ rows: L27Row[]; raw: any }> {
  await page.goto(formUrl, { waitUntil: 'networkidle' });
  const raw = await page.evaluate(async () => {
    const get = (u: string) => fetch(u, { headers: { Accept: 'application/json' } }).then((r) => r.json());
    return { services: await get('/v1/booking/services?location_id=1&mode=tags'), frequencies: await get('/v1/booking/frequencies?location_id=1') };
  });
  const rows: L27Row[] = [];
  const r2 = (n: number) => Math.round(n * 100) / 100;
  for (const svc of raw.services.services) {
    if (svc.hourly || !svc.pricing_parameters?.length) continue;
    const ranged = svc.pricing_parameters.find((p: any) => p.type === 'ranged');
    const flats = svc.pricing_parameters.filter((p: any) => p.type === 'flat');
    const full = flats.find((p: any) => /^bath/i.test(p.name));
    const half = flats.find((p: any) => /half/i.test(p.name));
    const addOns = [{ name: '', price: 0 }, ...svc.extras.filter((e: any) => !e.quantity_based && /deep|move/i.test(e.name))];
    for (const f of raw.frequencies) {
      const m = 1 - (f.percent || 0) / 100;
      for (const range of ranged?.ranges ?? [{ label: '', price: 0 }]) {
        for (let fb = full?.quantity_minimum ?? 0; fb <= (full?.quantity_maximum ?? 0); fb++) {
          for (let hb = half?.quantity_minimum ?? 0; hb <= Math.min(half?.quantity_maximum ?? 0, 3); hb++) {
            const base = svc.price + range.price + fb * (full?.price ?? 0) + hb * (half?.price ?? 0);
            for (const a of addOns) {
              if (a.name && f.percent) continue; // deep / move only harvested as one-time
              rows.push({
                service: svc.name,
                frequency: f.name,
                sqft: range.label,
                fullBaths: fb,
                halfBaths: hb,
                addOn: a.name,
                firstVisitPreTax: r2((base + a.price) * (f.exclude_first ? 1 : m)),
                recurringVisitPreTax: f.interval === 'o' ? null : r2(base * m),
              });
            }
          }
        }
      }
    }
  }
  log(`  ${rows.length} combinations expanded from the price feed`);
  return { rows, raw };
}
