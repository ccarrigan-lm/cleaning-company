import { chromium, Browser, BrowserContext, Page } from 'playwright';
import { Settings } from '../config';

export interface NetworkLogEntry {
  method: string;
  url: string;
  blocked: boolean;
}

export interface BrowserSession {
  browser: Browser;
  context: BrowserContext;
  page: Page;
  networkPosts: NetworkLogEntry[];
  close: () => Promise<void>;
}

/**
 * Launches a fresh, visible browser with no saved profile (no cookies or sessions
 * persist between runs). Installs the submission guard before any page loads.
 */
export async function launch(settings: Settings): Promise<BrowserSession> {
  const channel = settings.browser.channel && settings.browser.channel !== 'chromium' ? settings.browser.channel : undefined;
  let browser: Browser;
  try {
    browser = await chromium.launch({ channel, headless: settings.browser.headless, slowMo: settings.browser.slowMoMs });
  } catch (err) {
    throw new Error(
      `Could not launch browser (channel="${settings.browser.channel}"). ` +
        `Set "browser.channel" in config/settings.json to "msedge", "chrome", or "chromium" ` +
        `(chromium requires "npx playwright install chromium"). Original error: ${(err as Error).message}`,
    );
  }
  const context = await browser.newContext({ viewport: settings.browser.viewport, locale: 'en-US', timezoneId: 'America/New_York' });
  context.setDefaultNavigationTimeout(settings.timing.navigationTimeoutMs);
  const networkPosts = await installSubmissionGuard(context, settings);
  const page = await context.newPage();
  return {
    browser,
    context,
    page,
    networkPosts,
    close: async () => {
      await context.close().catch(() => undefined);
      await browser.close().catch(() => undefined);
    },
  };
}

/**
 * Network-level safety net: aborts non-GET requests that look like booking, lead,
 * account or payment submissions. Every non-GET request is logged for the evidence record.
 * The adapters also never click submit buttons; this is the second layer.
 */
async function installSubmissionGuard(context: BrowserContext, settings: Settings): Promise<NetworkLogEntry[]> {
  const log: NetworkLogEntry[] = [];
  const patterns = settings.safety.blockedRequestPatterns.map((p) => new RegExp(p, 'i'));
  await context.route('**/*', async (route) => {
    const req = route.request();
    const method = req.method();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return route.continue();
    const url = req.url();
    const blocked = !settings.safety.allowSubmission && patterns.some((re) => re.test(url));
    log.push({ method, url: redactUrl(url), blocked });
    if (blocked) {
      console.warn(`  [guard] BLOCKED ${method} ${redactUrl(url)}`);
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });
  return log;
}

function redactUrl(url: string): string {
  try {
    const u = new URL(url);
    return `${u.origin}${u.pathname}`; // drop query strings (may carry identifiers)
  } catch {
    return url.split('?')[0];
  }
}

/** Throws if a click target's text looks like a booking/submit/payment control. */
export async function assertSafeToClick(page: Page, selector: string, settings: Settings): Promise<void> {
  if (settings.safety.allowSubmission) return;
  const text = ((await page.locator(selector).first().innerText().catch(() => '')) || '').toLowerCase().trim();
  const hit = settings.safety.blockedButtonText.find((t) => text.includes(t));
  if (hit) throw new Error(`Safety guard: refusing to click "${text}" (matches "${hit}").`);
}
