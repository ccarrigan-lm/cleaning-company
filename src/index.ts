#!/usr/bin/env node
import { getAdapter, ADAPTERS } from './adapters';
import { AdapterResult } from './adapters/types';
import { launch } from './capture/browser';
import { waitForEnter } from './capture/verification';
import { loadCompanies, loadSettings, outputDir } from './config';
import { BASELINE_PROFILE_ID, getProfile, PROFILES } from './scenarios/profiles';
import { getScenario, SCENARIOS } from './scenarios/scenarios';
import { exportCsv } from './storage/csvExport';
import { harvestBookingKoala, writeRows } from './harvest/bookingkoala';
import { harvestLaunch27 } from './harvest/launch27';
import path from 'path';
import { evidenceDir, loadQuotes, saveQuote } from './storage/jsonStore';
import { QuoteRecord } from './types';

const USAGE = `
cleaning-price-research

  npm run open -- [company]                 Open a visible browser at the company's quote page
  npm run quote -- [options]                Capture one quote (never submits a booking)
      --company   <id>    default: scrub-lou
      --profile   <id>    default: ${BASELINE_PROFILE_ID}
      --scenario  <id>    default: baseline
      --keep-open         leave the browser open until you press Enter
  npm run harvest -- <company|all>          Walk EVERY size/service/frequency combination on the
                                            company's online form and save the full price grid
                                            (output/harvest/<company>/<date>.csv). Never submits anything.
  npm run list                              List companies, profiles and scenarios
  npm run export-csv                        Rebuild output/quotes.csv from saved JSON
`;

function parseArgs(argv: string[]) {
  const positional: string[] = [];
  const flags: Record<string, string | boolean> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith('--')) {
        flags[key] = next;
        i++;
      } else flags[key] = true;
    } else positional.push(a);
  }
  return { positional, flags };
}

async function cmdOpen(companyId: string) {
  const settings = loadSettings();
  const company = loadCompanies()[companyId];
  if (!company) throw new Error(`Unknown company "${companyId}"`);
  const url = company.quotePageUrl || company.formUrl;
  const session = await launch({ ...settings, browser: { ...settings.browser, headless: false } });
  try {
    console.log(`Opening ${company.name}: ${url}`);
    await session.page.goto(url, { waitUntil: 'domcontentloaded' });
    console.log(`Loaded: ${await session.page.title()}`);
    console.log('Submission guard is active. Inspect the form freely; do not enter personal details.');
    await waitForEnter('Press Enter here to close the browser... ');
  } finally {
    await session.close();
  }
}

async function cmdQuote(flags: Record<string, string | boolean>) {
  const settings = loadSettings();
  const companyId = String(flags.company ?? 'scrub-lou');
  const company = loadCompanies()[companyId];
  if (!company) throw new Error(`Unknown company "${companyId}"`);
  const adapter = getAdapter(companyId);
  const home = getProfile(String(flags.profile ?? BASELINE_PROFILE_ID));
  const scenario = getScenario(String(flags.scenario ?? 'baseline'));
  const out = outputDir(settings);

  const started = new Date();
  const stamp = started.toISOString().replace(/[:.]/g, '-');
  const runId = `${stamp}_${companyId}_${home.id}_${scenario.id}`;
  const evDir = evidenceDir(out, companyId);
  const interactive = Boolean(process.stdin.isTTY) && !settings.browser.headless;

  console.log(`\n${company.name} | profile=${home.id} (${home.label}) | scenario=${scenario.id} (${scenario.label})`);
  const session = await launch(settings);
  let r: AdapterResult;
  try {
    r = await adapter.capture({
      page: session.page,
      settings,
      company,
      home,
      scenario,
      evidenceDir: evDir,
      evidenceBaseName: runId,
      interactive,
    });
  } catch (err) {
    // Unexpected failure: still save an error record with a screenshot.
    const shot = `${evDir}/${runId}__error.png`;
    await session.page.screenshot({ path: shot, fullPage: true }).catch(() => undefined);
    r = {
      status: 'error',
      statusDetail: (err as Error).message,
      sourceUrl: session.page.url(),
      actual: { extras: [], notes: [] },
      price: { currency: 'USD', displayedTotal: null, totalBeforeTax: null, tax: null, taxRatePercent: null, fees: [], discounts: [], extras: [], firstVisitTotal: null, recurringVisitTotal: null },
      terms: { firstCleanRequirement: '', minimumCommitment: '', priceQualifications: [] },
      screenshotPath: shot,
      summaryScreenshotPath: null,
      capturedPriceText: '',
      summaryRows: [],
    };
  }

  const record: QuoteRecord = {
    schemaVersion: 1,
    runId,
    company: company.name,
    companyId,
    profileId: home.id,
    scenarioId: scenario.id,
    timestamp: started.toISOString(),
    sourceUrl: r.sourceUrl,
    formUrl: company.formUrl,
    requested: { home, scenario },
    actual: r.actual,
    status: r.status,
    statusDetail: r.statusDetail,
    price: r.price,
    terms: r.terms,
    evidence: {
      screenshotPath: r.screenshotPath,
      summaryScreenshotPath: r.summaryScreenshotPath,
      capturedPriceText: r.capturedPriceText,
      summaryRows: r.summaryRows,
      networkPosts: session.networkPosts,
    },
    durationMs: Date.now() - started.getTime(),
  };

  const file = saveQuote(out, record);
  const csv = exportCsv(out, loadQuotes(out));

  console.log(`\n  status:        ${record.status}`);
  console.log(`  detail:        ${record.statusDetail}`);
  if (record.price.displayedTotal) {
    console.log(`  total:         $${record.price.displayedTotal.amount.toFixed(2)}`);
    if (record.price.totalBeforeTax) console.log(`  before tax:    $${record.price.totalBeforeTax.amount.toFixed(2)}`);
    if (record.price.tax) console.log(`  tax:           $${record.price.tax.amount.toFixed(2)}${record.price.taxRatePercent !== null ? ` (${record.price.taxRatePercent}%)` : ''}`);
  }
  console.log(`  selections:    ${[record.actual.cleaningType, record.actual.frequency, `${record.actual.bedrooms} bd`, `${record.actual.bathrooms} ba`, record.actual.squareFeet, ...record.actual.extras].filter(Boolean).join(' | ')}`);
  console.log(`  blocked posts: ${session.networkPosts.filter((p) => p.blocked).length}`);
  console.log(`  json:          ${file}`);
  console.log(`  csv:           ${csv}`);
  if (record.evidence.screenshotPath) console.log(`  screenshot:    ${record.evidence.screenshotPath}`);

  if (flags['keep-open']) await waitForEnter('\nBrowser left open for a manual check. Press Enter to close... ');
  await session.close();
  if (record.status === 'error') process.exitCode = 1;
}

async function cmdHarvest(target: string) {
  const settings = loadSettings();
  const companies = loadCompanies();
  const ids = target === 'all' ? Object.keys(companies).filter((id) => companies[id].harvest) : [target];
  const out = outputDir(settings);
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  for (const id of ids) {
    const c = companies[id];
    if (!c?.harvest) throw new Error(`No harvest config for "${id}" in config/companies.json`);
    console.log(`\nHarvesting ${c.name} (${c.platform})`);
    const session = await launch(settings);
    try {
      const dir = path.join(out, 'harvest', id);
      if (c.harvest.type === 'bookingkoala') {
        const zip = String(process.env.ZIP ?? '40217');
        const { rows, taxRate } = await harvestBookingKoala(session.page, { formUrl: c.formUrl, zip, labels: c.harvest.labels!, services: c.harvest.services });
        const files = writeRows(dir, `${stamp}_zip${zip}`, rows.map((r) => ({ ...r, company: c.name, zip, taxRatePct: taxRate })));
        console.log(`  ${rows.length} rows, ${rows.filter((r) => !r.verified).length} unverified -> ${files.csv}`);
      } else {
        const { rows, raw } = await harvestLaunch27(session.page, c.formUrl);
        const files = writeRows(dir, stamp, rows.map((r) => ({ ...r, company: c.name })));
        writeRows(dir, `${stamp}_raw-feed`, [raw]);
        console.log(`  ${rows.length} rows -> ${files.csv}`);
      }
      console.log(`  blocked submission requests: ${session.networkPosts.filter((p) => p.blocked).length}`);
    } finally {
      await session.close();
    }
    await new Promise((r) => setTimeout(r, settings.timing.pauseBetweenScenariosMs));
  }
}

function cmdList() {
  const companies = loadCompanies();
  console.log('\nCompanies:');
  for (const [id, c] of Object.entries(companies)) console.log(`  ${id.padEnd(28)} ${c.name}${ADAPTERS[id] ? '' : '  (no adapter yet)'}`);
  console.log('\nProfiles:');
  for (const p of PROFILES) console.log(`  ${p.id.padEnd(28)} ${p.label}  ZIP ${p.zip}`);
  console.log('\nScenarios:');
  for (const s of SCENARIOS) console.log(`  ${s.id.padEnd(28)} ${s.label}`);
}

function cmdExport() {
  const settings = loadSettings();
  const out = outputDir(settings);
  const quotes = loadQuotes(out);
  console.log(`Exported ${quotes.length} quote(s) to ${exportCsv(out, quotes)}`);
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const { positional, flags } = parseArgs(rest);
  switch (cmd) {
    case 'open':
      return cmdOpen(positional[0] ?? 'scrub-lou');
    case 'quote':
      return cmdQuote(flags);
    case 'harvest':
      return cmdHarvest(positional[0] ?? 'all');
    case 'list':
      return cmdList();
    case 'export-csv':
      return cmdExport();
    default:
      console.log(USAGE);
  }
}

main().catch((err) => {
  console.error(`\nError: ${err instanceof Error ? err.message : err}`);
  process.exitCode = 1;
});
