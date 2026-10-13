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
  harvest?: {
    type: 'bookingkoala' | 'launch27';
    labels?: { bedrooms: string; bathrooms: string; sqft: string };
    services?: string[];
  };
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

export function loadCompanies(): Record<string, CompanyConfig> {
  return readJson<Record<string, CompanyConfig>>('companies.json');
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
