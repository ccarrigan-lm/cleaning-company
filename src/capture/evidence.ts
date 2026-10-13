import fs from 'fs';
import path from 'path';
import { Locator, Page } from 'playwright';

export interface ScreenshotPaths {
  fullPage: string | null;
  element: string | null;
}

/** Saves a full-page screenshot and (optionally) a close-up of the price panel. */
export async function captureScreenshots(page: Page, dir: string, baseName: string, priceArea?: Locator): Promise<ScreenshotPaths> {
  fs.mkdirSync(dir, { recursive: true });
  const fullPage = path.join(dir, `${baseName}.png`);
  const element = path.join(dir, `${baseName}__price.png`);
  const out: ScreenshotPaths = { fullPage: null, element: null };
  try {
    await page.screenshot({ path: fullPage, fullPage: true });
    out.fullPage = fullPage;
  } catch (err) {
    console.warn(`  [evidence] full-page screenshot failed: ${(err as Error).message}`);
  }
  if (priceArea) {
    try {
      await priceArea.scrollIntoViewIfNeeded();
      await priceArea.screenshot({ path: element });
      out.element = element;
    } catch (err) {
      console.warn(`  [evidence] price-panel screenshot failed: ${(err as Error).message}`);
    }
  }
  return out;
}
