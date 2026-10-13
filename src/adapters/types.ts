import { Page } from 'playwright';
import { CompanyConfig, Settings } from '../config';
import { ActualSelections, HomeProfile, PriceResult, QuoteStatus, Scenario, Terms } from '../types';

export interface AdapterContext {
  page: Page;
  settings: Settings;
  company: CompanyConfig;
  home: HomeProfile;
  scenario: Scenario;
  /** Folder for this run's screenshots. */
  evidenceDir: string;
  /** File-name stem for screenshots (no extension). */
  evidenceBaseName: string;
  /** True when a person is at the keyboard and can solve a CAPTCHA / verification. */
  interactive: boolean;
}

/** What an adapter returns; the runner adds identity, timing and network log. */
export interface AdapterResult {
  status: QuoteStatus;
  statusDetail: string;
  sourceUrl: string;
  actual: ActualSelections;
  price: PriceResult;
  terms: Terms;
  screenshotPath: string | null;
  summaryScreenshotPath: string | null;
  capturedPriceText: string;
  summaryRows: { label: string; value: string }[];
}

export interface Adapter {
  id: string;
  /** Translate a common scenario into this site's form, read the displayed price, never submit. */
  capture(ctx: AdapterContext): Promise<AdapterResult>;
}

export function emptyPrice(): PriceResult {
  return {
    currency: 'USD',
    displayedTotal: null,
    totalBeforeTax: null,
    tax: null,
    taxRatePercent: null,
    fees: [],
    discounts: [],
    extras: [],
    firstVisitTotal: null,
    recurringVisitTotal: null,
  };
}

export function emptyTerms(): Terms {
  return { firstCleanRequirement: '', minimumCommitment: '', priceQualifications: [] };
}
