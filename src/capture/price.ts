import { Page } from 'playwright';
import { Money } from '../types';

/** Parses "$1,234.50", "1234.5 ", "USD 99" → number. Returns null if no amount is present. */
export function parseMoney(text: string | null | undefined): number | null {
  if (!text) return null;
  const m = text.replace(/\s+/g, ' ').match(/-?\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?/);
  if (!m) return null;
  const whole = m[1].replace(/,/g, '');
  const cents = m[2] ? `.${m[2].padEnd(2, '0')}` : '';
  const n = Number(`${whole}${cents}`);
  if (!Number.isFinite(n)) return null;
  return text.trim().startsWith('-') ? -n : n;
}

export function toMoney(text: string | null | undefined): Money | null {
  const amount = parseMoney(text);
  return amount === null ? null : { amount, text: (text ?? '').replace(/\s+/g, ' ').trim() };
}

export const round2 = (n: number) => Math.round(n * 100) / 100;

/**
 * Waits until the text returned by `read` has been identical for `stableMs`.
 * Returns the stable text, or throws on timeout. Empty text never counts as stable.
 */
export async function waitForStableText(
  page: Page,
  read: () => Promise<string>,
  opts: { stableMs: number; timeoutMs: number; pollMs?: number },
): Promise<string> {
  const poll = opts.pollMs ?? 250;
  const deadline = Date.now() + opts.timeoutMs;
  let last = '';
  let since = Date.now();
  while (Date.now() < deadline) {
    const now = (await read().catch(() => '')).trim();
    if (now !== last) {
      last = now;
      since = Date.now();
    } else if (now && Date.now() - since >= opts.stableMs) {
      return now;
    }
    await page.waitForTimeout(poll);
  }
  throw new Error(`Price did not settle within ${opts.timeoutMs} ms (last value: "${last}")`);
}
