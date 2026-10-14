import fs from 'fs';
import path from 'path';

/** Project root (one level above dist/ or src/). */
export const ROOT = path.resolve(__dirname, '..');

export interface Settings {
  contactEmail: string;
  outputDir: string;
  browser: {
    channel: string; // "msedge", "chrome", or "chromium" (Playwright's bundled build)
    headless: boolean;
    slowMoMs: number;
    viewport: { width: number; height: number };
  };
  timing: {
    navigationTimeoutMs: number;
    priceStableMs: number;
    priceTimeoutMs: number;
    pauseBetweenScenariosMs: number;
  };
  safety: {
    allowSubmission: boolean;
    blockedButtonText: string[];
    blockedRequestPatterns: string[];
  };
}

export interface CompanyConfig {
  name: string;
  website: string;
  quotePageUrl: string;
  formUrl: string;
  platform: string;
  notes: string;
  /** City id from config/cities.json (default: louisville). */
  city?: string;
  /** ZIP used for pricing (default: the city's ZIP). */
  zip?: string;
  /** "manual" for hand-configured entries, "discovered" for ones found by `npm run discover`. */
  source?: 'manual' | 'discovered';
  harvest?: {
    type: 'bookingkoala' | 'launch27';
    /** Optional: label text of the size selects. Detected automatically when omitted. */
    labels?: { bedrooms: string; bathrooms: string; sqft: string };
    services?: string[];
  };
}

export interface City {
  id: string;
  name: string;
  state: string;
  zip: string;
  home?: boolean;
}

function readJson<T>(file: string): T {
  const full = path.join(ROOT, 'config', file);
  return JSON.parse(fs.readFileSync(full, 'utf8')) as T;
}

/** Optional config/settings.local.json overrides (git-ignored). */
export function loadSettings(): Settings {
  const base = readJson<Settings>('settings.json');
  const localPath = path.join(ROOT, 'config', 'settings.local.json');
  let merged: Settings = base;
  if (fs.existsSync(localPath)) {
    const local = JSON.parse(fs.readFileSync(localPath, 'utf8'));
    merged = deepMerge(base, local);
  }
  // Environment overrides for quick switches
  if (process.env.BROWSER_CHANNEL) merged.browser.channel = process.env.BROWSER_CHANNEL;
  if (process.env.HEADLESS) merged.browser.headless = process.env.HEADLESS === '1' || process.env.HEADLESS === 'true';
  return merged;
}

export const DISCOVERED_FILE = path.join(ROOT, 'config', 'companies.discovered.json');

/** Hand-configured companies plus everything `npm run discover` found (hand entries win). */
export function loadCompanies(): Record<string, CompanyConfig> {
  const manual = readJson<Record<string, CompanyConfig>>('companies.json');
  for (const c of Object.values(manual)) c.source = c.source ?? 'manual';
  const found: Record<string, CompanyConfig> = fs.existsSync(DISCOVERED_FILE) ? JSON.parse(fs.readFileSync(DISCOVERED_FILE, 'utf8')) : {};
  const manualForms = new Set(Object.values(manual).map((c) => normUrl(c.formUrl)));
  const out: Record<string, CompanyConfig> = { ...manual };
  for (const [id, c] of Object.entries(found)) {
    if (out[id] || manualForms.has(normUrl(c.formUrl))) continue;
    out[id] = { ...c, source: 'discovered' };
  }
  return out;
}

export function loadCities(): City[] {
  return readJson<{ cities: City[] }>('cities.json').cities;
}

export function cityOf(c: CompanyConfig, cities = loadCities()): City {
  const id = c.city ?? 'louisville';
  const city = cities.find((x) => x.id === id);
  if (!city) throw new Error(`Unknown city "${id}" (see config/cities.json)`);
  return city;
}

export function normUrl(u: string): string {
  return (u || '').toLowerCase().replace(/^https?:\/\/(www\.)?/, '').replace(/[?#].*$/, '').replace(/\/+$/, '');
}

export function outputDir(settings: Settings): string {
  return path.resolve(ROOT, settings.outputDir);
}

function deepMerge<T>(a: T, b: Partial<T>): T {
  if (Array.isArray(a) || typeof a !== 'object' || a === null) return (b ?? a) as T;
  const out: any = { ...a };
  for (const [k, v] of Object.entries(b ?? {})) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) ? deepMerge((a as any)[k], v as any) : v;
  }
  return out;
}
