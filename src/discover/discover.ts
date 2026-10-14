import fs from 'fs';
import path from 'path';
import { BrowserContext, Page } from 'playwright';
import { City, CompanyConfig, DISCOVERED_FILE, normUrl } from '../config';

/**
 * Finds residential cleaning companies in a city and detects which ones show an instant online
 * price we can harvest (BookingKoala or Launch27 forms, including ones on the company's own domain).
 *
 * 1. Search: runs a few web searches per city in the browser (DuckDuckGo HTML, Bing as fallback)
 *    and keeps the company websites (directories and marketplaces are filtered out).
 * 2. Probe: opens each website, its booking/pricing pages and common booking paths, and watches the
 *    page DOM, iframes and network requests for booking-platform signatures.
 *
 * Only GET page loads. Nothing is typed into any form here, so no inquiry is ever sent.
 */

export type Platform = 'bookingkoala' | 'launch27' | 'zenmaid' | 'maidily' | 'jobber' | 'housecallpro' | 'booking-other' | 'none';

export interface ProbeResult {
  city: string;
  domain: string;
  website: string;
  name: string;
  platform: Platform;
  formUrl: string;
  harvestable: boolean;
  pagesChecked: number;
  evidence: string;
  error: string;
}

const SEARCH_QUERIES = [
  'house cleaning service {city} {state}',
  'maid service {city} {state}',
  'residential cleaning company {city} {state} book online',
  'deep cleaning service {city} {state} pricing',
  'move out cleaning {city} {state}',
];

/** Directories, marketplaces, national lead-gen sites and big platforms: never a company site. */
const SKIP_HOSTS = [
  'yelp.', 'thumbtack.', 'angi.', 'angieslist.', 'homeadvisor.', 'houzz.', 'bark.com', 'care.com', 'taskrabbit.', 'handy.com',
  'tidy.com', 'homeaglow.', 'nextdoor.', 'facebook.', 'instagram.', 'linkedin.', 'twitter.', 'x.com', 'youtube.', 'tiktok.',
  'pinterest.', 'reddit.', 'bbb.org', 'yellowpages.', 'mapquest.', 'google.', 'bing.', 'duckduckgo.', 'wikipedia.', 'indeed.',
  'glassdoor.', 'ziprecruiter.', 'craigslist.', 'expertise.com', 'threebestrated.', 'homeguide.', 'porch.', 'networx.',
  'fixr.com', 'lawnstarter.', 'bookingkoala.com', 'launch27.com', 'zenmaid.com', 'groupon.', 'amazon.', 'apple.com',
  'chamberofcommerce.', 'manta.com', 'superpages.', 'local.com', 'dexknows.', 'birdeye.', 'trustpilot.', 'zoominfo.',
  'buildzoom.', 'lantern.llc', 'urlscan.io', 'contractorplus.', 'homeyou.', 'clutch.co', 'upcity.', 'durable.site',
  'wix.com', 'squarespace.com', 'godaddy.', 'weebly.', 'sites.google.', 'patch.com', 'wsj.', 'nytimes.', 'gov',
  '.edu', 'redfin.', 'zillow.', 'realtor.', 'apartments.com', 'experience.com', 'quora.', 'medium.com',
];

const BOOKING_LINK = /book|quote|pric|estimate|schedule|rates|cost|instant/i;
const COMMON_PATHS = ['/booknow', '/book-now', '/book-online', '/booking', '/book', '/pricing', '/get-a-quote', '/instant-quote'];

function hostOf(u: string): string {
  try {
    return new URL(u).hostname.toLowerCase().replace(/^www\./, '');
  } catch {
    return '';
  }
}

export function isCompanyHost(host: string): boolean {
  if (!host || !host.includes('.')) return false;
  return !SKIP_HOSTS.some((s) => host.includes(s) || host.endsWith(s));
}

/** Runs the city's searches and returns unique company homepages. */
export async function searchCity(page: Page, city: City, log = console.log, maxSites = 60): Promise<string[]> {
  const seen = new Map<string, string>();
  for (const tpl of SEARCH_QUERIES) {
    const q = tpl.replace('{city}', city.name).replace('{state}', city.state);
    let links = await searchDuckDuckGo(page, q).catch(() => [] as string[]);
    if (links.length < 5) links = links.concat(await searchBing(page, q).catch(() => [] as string[]));
    for (const l of links) {
      const h = hostOf(l);
      if (isCompanyHost(h) && !seen.has(h)) seen.set(h, `https://${h}/`);
    }
    log(`    search "${q}": ${links.length} results, ${seen.size} company sites so far`);
    await page.waitForTimeout(1500 + Math.random() * 1500);
    if (seen.size >= maxSites) break;
  }
  return [...seen.values()].slice(0, maxSites);
}

async function searchDuckDuckGo(page: Page, q: string): Promise<string[]> {
  await page.goto(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(q)}`, { waitUntil: 'domcontentloaded' });
  return page.$$eval('a.result__a', (as) =>
    as.map((a) => {
      const href = (a as HTMLAnchorElement).href;
      try {
        const u = new URL(href);
        return u.searchParams.get('uddg') || href;
      } catch {
        return href;
      }
    }),
  );
}

async function searchBing(page: Page, q: string): Promise<string[]> {
  const out: string[] = [];
  for (const first of [1, 11, 21]) {
    await page.goto(`https://www.bing.com/search?q=${encodeURIComponent(q)}&first=${first}`, { waitUntil: 'domcontentloaded' });
    out.push(...(await page.$$eval('li.b_algo h2 a', (as) => as.map((a) => (a as HTMLAnchorElement).href))));
  }
  return out;
}

interface Signal {
  platform: Platform;
  formUrl: string;
  evidence: string;
}

/** Classifies a URL seen in the page (iframe, link, script or network request). */
function signalFromUrl(u: string): Signal | null {
  let url: URL;
  try {
    url = new URL(u);
  } catch {
    return null;
  }
  const h = url.hostname.toLowerCase();
  const assetHost = /^(www|cdn|static|assets|app|api|images?|files|media|help|support|blog)\./;
  if (h.endsWith('.bookingkoala.com') && !assetHost.test(h)) {
    return { platform: 'bookingkoala', formUrl: `https://${h}/booknow`, evidence: `bookingkoala host ${h}` };
  }
  if (h.endsWith('.launch27.com') && !assetHost.test(h)) {
    return { platform: 'launch27', formUrl: `https://${h}/`, evidence: `launch27 host ${h}` };
  }
  if (/\/v1\/booking\/services/.test(url.pathname)) {
    return { platform: 'launch27', formUrl: `${url.origin}/`, evidence: `launch27 price feed ${url.origin}` };
  }
  if (/\/api\/v4\/get-tax-rate/.test(url.pathname)) {
    return { platform: 'bookingkoala', formUrl: '', evidence: `bookingkoala API on ${h}` };
  }
  if (/zenmaid\.com$/.test(h) && h !== 'www.zenmaid.com') return { platform: 'zenmaid', formUrl: u, evidence: `zenmaid ${h}` };
  if (/maidily\.com$/.test(h)) return { platform: 'maidily', formUrl: u, evidence: `maidily ${h}` };
  if (/getjobber\.com$/.test(h)) return { platform: 'jobber', formUrl: u, evidence: `jobber ${h}` };
  if (/housecallpro\.com$/.test(h)) return { platform: 'housecallpro', formUrl: u, evidence: `housecallpro ${h}` };
  return null;
}

const RANK: Record<Platform, number> = { bookingkoala: 9, launch27: 9, zenmaid: 3, maidily: 3, jobber: 2, housecallpro: 2, 'booking-other': 1, none: 0 };

export async function probeSite(context: BrowserContext, website: string, cityId: string, timeoutMs = 25000): Promise<ProbeResult> {
  const domain = hostOf(website);
  const res: ProbeResult = { city: cityId, domain, website, name: '', platform: 'none', formUrl: '', harvestable: false, pagesChecked: 0, evidence: '', error: '' };
  const page = await context.newPage();
  page.setDefaultNavigationTimeout(timeoutMs);
  let best: Signal | null = null;
  const consider = (s: Signal | null) => {
    if (!s) return;
    if (!best || RANK[s.platform] > RANK[best.platform] || (s.platform === best.platform && !best.formUrl && s.formUrl)) best = s;
  };
  page.on('request', (r) => consider(signalFromUrl(r.url())));
  page.on('framenavigated', (f) => consider(signalFromUrl(f.url())));

  const scan = async () => {
    res.pagesChecked++;
    // Iframes, links, scripts, and BookingKoala's own form markup on a custom domain.
    const found = await page
      .evaluate(() => {
        const urls = [
          ...[...document.querySelectorAll('iframe')].map((f) => (f as HTMLIFrameElement).src),
          ...[...document.querySelectorAll('a[href]')].map((a) => (a as HTMLAnchorElement).href),
          ...[...document.querySelectorAll('script[src]')].map((s) => (s as HTMLScriptElement).src),
        ];
        const bkMarkup = !!document.querySelector('#zipcode-value, .bk-form-extra-input, #booking-summary');
        return { urls, bkMarkup, href: location.href };
      })
      .catch(() => ({ urls: [] as string[], bkMarkup: false, href: '' }));
    for (const u of found.urls) consider(signalFromUrl(u));
    if (found.bkMarkup) consider({ platform: 'bookingkoala', formUrl: found.href.replace(/[?#].*$/, ''), evidence: `bookingkoala form markup at ${found.href}` });
  };

  try {
    await page.goto(website, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    res.name = cleanName(await page.title().catch(() => ''), domain);
    await scan();
    // Same-site links that look like booking / pricing pages.
    const links: string[] = await page
      .$$eval('a[href]', (as) => as.map((a) => ({ href: (a as HTMLAnchorElement).href, text: (a.textContent || '').trim() })))
      .then((ls) => ls.filter((l) => /book|quote|pric|estimate|schedule|rates|cost|instant/i.test(l.href + ' ' + l.text)).map((l) => l.href))
      .catch(() => []);
    const origin = new URL(page.url()).origin;
    const targets = [...new Set([...links.filter((l) => hostOf(l) === hostOf(origin) && BOOKING_LINK.test(l)), ...COMMON_PATHS.map((p) => origin + p)])].slice(0, 8);
    for (const t of targets) {
      const b = best as Signal | null;
      if (b && RANK[b.platform] >= 9 && b.formUrl) break;
      const resp = await page.goto(t, { waitUntil: 'domcontentloaded' }).catch(() => null);
      if (!resp || resp.status() >= 400) continue;
      await page.waitForTimeout(3000);
      await scan();
    }
  } catch (err) {
    res.error = (err as Error).message.split('\n')[0];
  } finally {
    await page.close().catch(() => undefined);
  }
  const b = best as Signal | null;
  if (b) {
    res.platform = b.platform;
    res.formUrl = b.formUrl;
    res.evidence = b.evidence;
  } else if (res.pagesChecked > 0) {
    res.platform = 'none';
  }
  res.harvestable = (res.platform === 'bookingkoala' || res.platform === 'launch27') && !!res.formUrl;
  return res;
}

function cleanName(title: string, domain: string): string {
  const t = title.split(/\s[|\-–—:]\s/)[0].trim();
  return t && t.length <= 60 ? t : domain;
}

export function slug(s: string): string {
  return s.toLowerCase().replace(/^www\./, '').replace(/\.(com|net|org|co|us|biz|info|pro|services?)$/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/** Adds harvestable results to config/companies.discovered.json (keeps earlier finds). */
export function saveDiscovered(results: ProbeResult[], existing: Record<string, CompanyConfig>): { added: number; file: string } {
  const found: Record<string, CompanyConfig> = fs.existsSync(DISCOVERED_FILE) ? JSON.parse(fs.readFileSync(DISCOVERED_FILE, 'utf8')) : {};
  const known = new Set([...Object.values(existing), ...Object.values(found)].map((c) => normUrl(c.formUrl)));
  let added = 0;
  for (const r of results) {
    if (!r.harvestable || known.has(normUrl(r.formUrl))) continue;
    let id = slug(r.domain);
    while (existing[id] || found[id]) id += '-2';
    found[id] = {
      name: r.name || r.domain,
      website: r.website,
      quotePageUrl: r.website,
      formUrl: r.formUrl,
      platform: r.platform === 'bookingkoala' ? 'BookingKoala' : 'Launch27',
      notes: `Found by npm run discover (${r.evidence}).`,
      city: r.city,
      source: 'discovered',
      harvest: { type: r.platform as 'bookingkoala' | 'launch27' },
    };
    known.add(normUrl(r.formUrl));
    added++;
  }
  fs.writeFileSync(DISCOVERED_FILE, JSON.stringify(found, null, 2));
  return { added, file: DISCOVERED_FILE };
}

export function appendCsv(file: string, rows: object[]) {
  if (!rows.length) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const keys = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const body = rows.map((r: any) => keys.map((k) => esc(r[k])).join(',')).join('\r\n') + '\r\n';
  if (!fs.existsSync(file)) fs.writeFileSync(file, '﻿' + keys.join(',') + '\r\n' + body);
  else fs.appendFileSync(file, body);
}
