#!/usr/bin/env node
import { getAdapter, ADAPTERS } from './adapters';
import { AdapterResult } from './adapters/types';
import { installSubmissionGuard, launch } from './capture/browser';
import { waitForEnter } from './capture/verification';
import { cityOf, loadCities, loadCompanies, loadSettings, outputDir } from './config';
import { appendCsv, probeSite, ProbeResult, saveDiscovered, searchCity } from './discover/discover';
import fs from 'fs';
import { spawnSync } from 'child_process';
import { BASELINE_PROFILE_ID, getProfile, PROFILES } from './scenarios/profiles';
import { getScenario, SCENARIOS } from './scenarios/scenarios';
import { exportCsv } from './storage/csvExport';
import { harvestBookingKoala, writeRows } from './harvest/bookingkoala';
import { harvestLaunch27 } from './harvest/launch27';
import { validateLouisville } from './validate/louisville';
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
      --city <id>         only companies in this city (config/cities.json)
      --skip-done         skip companies already harvested today
  npm run discover -- [city|all]            Search each city for cleaning companies, detect which ones
                                            have an instant-price booking form, and add them to
                                            config/companies.discovered.json for harvesting.
      --max-sites <n>     company websites to check per city (default 60)
  npm run collect                           discover + harvest + build the matrix, unattended
      --no-discover       skip discovery (just re-harvest everything known)
  npm run build-matrix                      rebuild research/market/<date>/ from saved harvests
  npm run validate:louisville               live-form checks: Red Feather, Maid 2 Clean, Launch27 spot checks
                                            (output/validation/<date>/ with screenshots; never submits)
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

async function cmdHarvest(target: string, flags: Record<string, string | boolean> = {}) {
  const settings = loadSettings();
  const companies = loadCompanies();
  const cities = loadCities();
  let ids = target === 'all' ? Object.keys(companies).filter((id) => companies[id].harvest) : [target];
  if (flags.city) ids = ids.filter((id) => (companies[id].city ?? 'louisville') === flags.city);
  const out = outputDir(settings);
  const now = new Date();
  const day = now.toISOString().slice(0, 10);
  const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const runLog = path.join(out, 'harvest', '_runs', `${stamp}.csv`);
  console.log(`Harvesting ${ids.length} companies. Run log: ${runLog}`);
  let n = 0;
  for (const id of ids) {
    n++;
    const c = companies[id];
    if (!c?.harvest) {
      console.log(`\n[${n}/${ids.length}] ${id}: no harvest config, skipped`);
      continue;
    }
    const city = cityOf(c, cities);
    const zip = String(process.env.ZIP ?? c.zip ?? city.zip);
    const dir = path.join(out, 'harvest', id);
    if (flags['skip-done'] && fs.existsSync(dir) && fs.readdirSync(dir).some((f) => f.startsWith(day) && f.endsWith('.csv') && !f.includes('raw') && !f.includes('extras'))) {
      console.log(`\n[${n}/${ids.length}] ${c.name}: already harvested today, skipped`);
      continue;
    }
    console.log(`\n[${n}/${ids.length}] Harvesting ${c.name} (${c.platform}, ${city.name} ${city.state}, ZIP ${zip})`);
    const started = Date.now();
    const status: any = { company: c.name, companyId: id, city: city.name, state: city.state, zip, platform: c.platform, source: c.source, formUrl: c.formUrl, rows: 0, unverified: 0, status: 'ok', detail: '', file: '', seconds: 0 };
    let session: Awaited<ReturnType<typeof launch>> | null = null;
    try {
      session = await launch(settings);
      const meta = { company: c.name, companyId: id, city: city.name, state: city.state, zip, platform: c.platform, captured: day };
      if (c.harvest.type === 'bookingkoala') {
        const deadline = started + Number(flags['max-minutes'] ?? 45) * 60000;
        const s = session;
        // Backstop: if the page itself hangs, close the browser shortly after the deadline.
        const kill = setTimeout(() => s.close(), deadline - Date.now() + 5 * 60000);
        const { rows, taxRate, form, partial, skipped } = await harvestBookingKoala(session.page, { formUrl: c.formUrl, zip, labels: c.harvest.labels, services: c.harvest.services, deadline }).finally(() => clearTimeout(kill));
        if (partial) status.status = 'partial';
        if (skipped.length) status.detail = `not offered: ${skipped.join(', ')}`;
        const files = writeRows(dir, `${stamp}_zip${zip}`, rows.map((r) => ({ ...meta, ...r, taxRatePct: taxRate })));
        writeRows(dir, `${stamp}_form`, [{ ...meta, ...form, dims: JSON.stringify(form.dims), services: form.services.join(' | '), frequencies: form.frequencies.join(' | '), taxRatePct: taxRate }]);
        Object.assign(status, { rows: rows.length, unverified: rows.filter((r) => !r.verified).length, file: files.csv });
        if (!rows.length) Object.assign(status, { status: 'no_prices', detail: 'form loaded but no price-changing selects were found (unsupported layout)' });
      } else {
        const { rows, raw, extras } = await harvestLaunch27(session.page, c.formUrl);
        const files = writeRows(dir, stamp, rows.map((r) => ({ ...meta, ...r })));
        writeRows(dir, `${stamp}_raw-feed`, [raw]);
        if (extras.length) writeRows(dir, `${stamp}_extras`, extras.map((e) => ({ ...meta, ...e })));
        Object.assign(status, { rows: rows.length, file: files.csv });
      }
      const blocked = session.networkPosts.filter((p) => p.blocked).length;
      if (blocked) status.detail = (status.detail ? status.detail + '; ' : '') + `${blocked} submission requests blocked`;
      console.log(`  ${status.rows} rows, ${status.unverified} unverified -> ${status.file}`);
    } catch (err) {
      Object.assign(status, { status: 'error', detail: (err as Error).message.split('\n')[0] });
      console.log(`  [error] ${status.detail} (continuing with the next company)`);
    } finally {
      await session?.close();
    }
    status.seconds = Math.round((Date.now() - started) / 1000);
    appendCsv(runLog, [status]);
    await new Promise((r) => setTimeout(r, settings.timing.pauseBetweenScenariosMs));
  }
  console.log(`\nDone. Run log: ${runLog}`);
}

async function cmdDiscover(target: string, flags: Record<string, string | boolean>) {
  const settings = loadSettings();
  const cities = loadCities().filter((c) => target === 'all' || c.id === target);
  if (!cities.length) throw new Error(`Unknown city "${target}" (see config/cities.json)`);
  const out = outputDir(settings);
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const csv = path.join(out, 'discovery', `${stamp}.csv`);
  const maxSites = Number(flags['max-sites'] ?? 60);
  const concurrency = Number(flags.concurrency ?? 4);
  let totalAdded = 0;
  for (const city of cities) {
    console.log(`\n=== ${city.name}, ${city.state}`);
    const session = await launch(settings);
    try {
      const sites = await searchCity(session.page, city, console.log, maxSites);
      console.log(`  checking ${sites.length} company websites for instant-price booking forms...`);
      const results: ProbeResult[] = [];
      const queue = [...sites];
      await Promise.all(
        Array.from({ length: concurrency }, async () => {
          while (queue.length) {
            const site = queue.shift()!;
            const ctx = await session.browser.newContext({ viewport: settings.browser.viewport, locale: 'en-US' });
            await installSubmissionGuard(ctx, settings);
            const r = await probeSite(ctx, site, city.id).catch((e) => ({ city: city.id, domain: site, website: site, name: '', platform: 'none', formUrl: '', harvestable: false, pagesChecked: 0, evidence: '', error: String(e) }) as ProbeResult);
            await ctx.close().catch(() => undefined);
            results.push(r);
            const tag = r.harvestable ? 'HARVESTABLE' : r.platform === 'none' ? (r.error ? 'error' : 'no instant price') : r.platform;
            console.log(`    ${r.domain.padEnd(40)} ${tag}${r.formUrl ? '  ' + r.formUrl : ''}`);
          }
        }),
      );
      appendCsv(csv, results);
      const { added } = saveDiscovered(results, loadCompanies());
      totalAdded += added;
      console.log(`  ${city.name}: ${results.filter((r) => r.harvestable).length} harvestable, ${added} new added to config/companies.discovered.json`);
    } catch (err) {
      console.log(`  [error] ${city.name}: ${(err as Error).message.split('\n')[0]} (continuing)`);
    } finally {
      await session.close();
    }
  }
  console.log(`\nDiscovery done: ${totalAdded} new harvestable companies. Full list: ${csv}`);
}

/** Runs research/build_market.py with whichever Python is installed. */
function buildMatrix() {
  const script = path.join(__dirname, '..', 'research', 'build_market.py');
  for (const py of ['python3', 'python', 'py']) {
    const r = spawnSync(py, [script], { stdio: 'inherit' });
    if (!r.error) {
      if (r.status !== 0) console.log(`\n[warn] matrix build exited with code ${r.status}`);
      return;
    }
  }
  console.log('\n[warn] Python not found, so the matrix workbook was not built. Install Python 3 + openpyxl, then run: npm run build-matrix');
}

function cmdList() {
  const companies = loadCompanies();
  console.log('\nCompanies:');
  for (const [id, c] of Object.entries(companies)) console.log(`  ${id.padEnd(34)} ${c.name.padEnd(40)} ${(c.city ?? 'louisville').padEnd(14)} ${c.platform}${c.source === 'discovered' ? ' (discovered)' : ''}`);
  console.log('\nCities:');
  for (const c of loadCities()) console.log(`  ${c.id.padEnd(16)} ${c.name}, ${c.state}  ZIP ${c.zip}`);
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
      return cmdHarvest(positional[0] ?? 'all', flags);
    case 'discover':
      return cmdDiscover(positional[0] ?? 'all', flags);
    case 'collect':
      if (!flags['no-discover']) await cmdDiscover(String(flags.city ?? 'all'), flags);
      await cmdHarvest('all', { ...flags, 'skip-done': true });
      return buildMatrix();
    case 'build':
      return buildMatrix();
    case 'validate':
      if ((positional[0] ?? 'louisville') !== 'louisville') throw new Error('Only "louisville" validation is defined');
      await validateLouisville(loadSettings(), outputDir(loadSettings()));
      return;
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
