import fs from 'fs';
import path from 'path';
import { LineItem, QuoteRecord } from '../types';

const items = (xs: LineItem[]) => xs.map((x) => `${x.label}: ${x.amount ?? 'undisclosed'}`).join('; ');
const num = (n: number | null | undefined) => (n === null || n === undefined ? '' : n.toFixed(2));

/** Flattens every saved JSON quote into one CSV for Excel. Undisclosed amounts stay blank. */
export function exportCsv(outputRoot: string, quotes: QuoteRecord[]): string {
  const rows: Record<string, string | number>[] = quotes.map((q) => ({
    run_id: q.runId,
    company: q.company,
    profile_id: q.profileId,
    scenario_id: q.scenarioId,
    timestamp: q.timestamp,
    source_url: q.sourceUrl,
    status: q.status,
    status_detail: q.statusDetail,
    // Home (requested)
    zip: q.requested.home.zip,
    square_feet: q.requested.home.squareFeet,
    bedrooms: q.requested.home.bedrooms,
    bathrooms: q.requested.home.bathrooms,
    condition: q.requested.home.condition,
    pets: q.requested.home.pets,
    // Service (requested)
    cleaning_type: q.requested.scenario.cleaningType,
    frequency: q.requested.scenario.frequency,
    extras_requested: q.requested.scenario.extras.join('; '),
    areas_only: (q.requested.scenario.areasOnly ?? []).join('; '),
    // Actual form selections
    actual_square_feet: q.actual.squareFeet ?? '',
    actual_bedrooms: q.actual.bedrooms ?? '',
    actual_bathrooms: q.actual.bathrooms ?? '',
    actual_cleaning_type: q.actual.cleaningType ?? '',
    actual_frequency: q.actual.frequency ?? '',
    actual_extras: q.actual.extras.join('; '),
    actual_excluded_areas: (q.actual.excludedAreas ?? []).join('; '),
    selection_notes: q.actual.notes.join(' | '),
    // Price
    currency: q.price.currency,
    displayed_total: num(q.price.displayedTotal?.amount),
    total_before_tax: num(q.price.totalBeforeTax?.amount),
    tax: num(q.price.tax?.amount),
    tax_rate_pct: q.price.taxRatePercent ?? '',
    first_visit_total: num(q.price.firstVisitTotal?.amount),
    recurring_visit_total: num(q.price.recurringVisitTotal?.amount),
    fees: items(q.price.fees),
    discounts: items(q.price.discounts),
    extras_priced: items(q.price.extras),
    // Terms
    first_clean_requirement: q.terms.firstCleanRequirement,
    minimum_commitment: q.terms.minimumCommitment,
    price_qualifications: q.terms.priceQualifications.join(' | '),
    // Evidence
    screenshot: q.evidence.screenshotPath ?? '',
    price_screenshot: q.evidence.summaryScreenshotPath ?? '',
    captured_price_text: q.evidence.capturedPriceText,
  }));

  const headers = rows.length ? Object.keys(rows[0]) : ['run_id'];
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [headers.join(','), ...rows.map((r) => headers.map((h) => esc(r[h])).join(','))].join('\r\n');
  const file = path.join(outputRoot, 'quotes.csv');
  fs.mkdirSync(outputRoot, { recursive: true });
  fs.writeFileSync(file, '﻿' + csv, 'utf8'); // BOM so Excel reads UTF-8
  return file;
}
