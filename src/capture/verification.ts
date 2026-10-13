import readline from 'readline';
import { Page } from 'playwright';

const CHALLENGE_SELECTORS = [
  'iframe[src*="recaptcha"]',
  'iframe[src*="hcaptcha"]',
  'iframe[src*="challenges.cloudflare.com"]',
  '#challenge-form',
  'input[autocomplete="one-time-code"]',
];
const CHALLENGE_TEXT = /verify you are human|are you a robot|complete the security check|enter the code we sent|verification code/i;

/** Returns a short description if the page is showing a CAPTCHA, login wall or code prompt. */
export async function detectVerification(page: Page): Promise<string | null> {
  for (const sel of CHALLENGE_SELECTORS) {
    if (await page.locator(sel).first().isVisible().catch(() => false)) return `challenge element visible: ${sel}`;
  }
  const text = await page.locator('body').innerText().catch(() => '');
  const m = text.match(CHALLENGE_TEXT);
  return m ? `challenge text visible: "${m[0]}"` : null;
}

/** Waits for the person at the keyboard to press Enter. */
export function waitForEnter(prompt: string): Promise<void> {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, () => {
      rl.close();
      resolve();
    });
  });
}

/**
 * If a challenge is showing: in interactive mode, pause for the person to solve it;
 * otherwise return a description so the caller can record verification_required.
 */
export async function handleVerification(page: Page, interactive: boolean): Promise<string | null> {
  const found = await detectVerification(page);
  if (!found) return null;
  if (!interactive) return found;
  console.log(`\n  [pause] ${found}`);
  await waitForEnter('  Solve it in the browser window, then press Enter here to continue... ');
  const still = await detectVerification(page);
  return still;
}
