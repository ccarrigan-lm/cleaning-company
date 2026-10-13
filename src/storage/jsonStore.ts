import fs from 'fs';
import path from 'path';
import { QuoteRecord } from '../types';

export function quotesDir(outputRoot: string): string {
  return path.join(outputRoot, 'quotes');
}

export function evidenceDir(outputRoot: string, companyId: string): string {
  return path.join(outputRoot, 'evidence', companyId);
}

/** Writes one JSON file per captured quote: output/quotes/<runId>.json */
export function saveQuote(outputRoot: string, record: QuoteRecord): string {
  const dir = quotesDir(outputRoot);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${record.runId}.json`);
  // Store paths relative to the output folder so the folder can be moved/zipped.
  const portable: QuoteRecord = {
    ...record,
    evidence: {
      ...record.evidence,
      screenshotPath: rel(outputRoot, record.evidence.screenshotPath),
      summaryScreenshotPath: rel(outputRoot, record.evidence.summaryScreenshotPath),
    },
  };
  fs.writeFileSync(file, JSON.stringify(portable, null, 2), 'utf8');
  return file;
}

export function loadQuotes(outputRoot: string): QuoteRecord[] {
  const dir = quotesDir(outputRoot);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as QuoteRecord);
}

function rel(root: string, p: string | null): string | null {
  return p ? path.relative(root, p).split(path.sep).join('/') : null;
}
