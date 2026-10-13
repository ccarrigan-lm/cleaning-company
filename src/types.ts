// Shared data model. JSON is the detailed record; CSV is a flattened export.

export type CleaningType = 'standard' | 'deep' | 'move_in_out';
export type Frequency = 'one_time' | 'weekly' | 'biweekly' | 'every_4_weeks';
export type Condition = 'light' | 'average' | 'heavy';
export type Extra = 'oven_interior' | 'fridge_interior' | 'interior_windows' | 'basement';
export type Area = 'kitchen' | 'bathrooms' | 'bedrooms' | 'living_areas';

export interface HomeProfile {
  id: string;
  label: string;
  zip: string;
  squareFeet: number;
  bedrooms: number;
  bathrooms: number; // halves allowed, e.g. 2.5
  condition: Condition;
  pets: 'none';
}

export interface Scenario {
  id: string;
  label: string;
  cleaningType: CleaningType;
  frequency: Frequency;
  extras: Extra[];
  /** Undefined = whole home. Otherwise only these areas are cleaned. */
  areasOnly?: Area[];
}

export type QuoteStatus =
  | 'success'
  | 'manual_quote_required'
  | 'verification_required'
  | 'unsupported_option'
  | 'not_implemented'
  | 'extraction_failed'
  | 'error';

/** What we asked for, in our common vocabulary. */
export interface RequestedSettings {
  home: HomeProfile;
  scenario: Scenario;
}

/** What was actually selected on the competitor's form (their vocabulary). */
export interface ActualSelections {
  zip?: string;
  squareFeet?: string; // e.g. "1500 - 1999 Sq Ft"
  bedrooms?: string;
  bathrooms?: string;
  condition?: string; // blank when the form has no condition field
  pets?: string;
  cleaningType?: string;
  frequency?: string;
  extras: string[];
  excludedAreas?: string[];
  notes: string[]; // mismatches between requested and actual
}

export interface Money {
  amount: number;
  text: string; // exactly as displayed
}

export interface LineItem {
  label: string;
  amount: number | null; // null if not disclosed
  text: string;
}

export interface PriceResult {
  currency: 'USD';
  /** Final displayed total, including tax when the site adds it. */
  displayedTotal: Money | null;
  /** Total before tax, when displayed separately. */
  totalBeforeTax: Money | null;
  /** Tax amount when shown (or derived from two displayed totals; see taxNote). */
  tax: Money | null;
  taxRatePercent: number | null;
  taxNote?: string;
  fees: LineItem[];
  discounts: LineItem[];
  extras: LineItem[];
  /** Recurring service: first visit vs subsequent visits, when they differ and are shown. */
  firstVisitTotal: Money | null;
  recurringVisitTotal: Money | null;
}

export interface Terms {
  firstCleanRequirement: string; // "" when not stated
  minimumCommitment: string;
  priceQualifications: string[];
}

export interface Evidence {
  screenshotPath: string | null; // full page
  summaryScreenshotPath: string | null; // price panel only
  capturedPriceText: string; // raw text of the price/summary area
  summaryRows: { label: string; value: string }[];
  networkPosts: { method: string; url: string; blocked: boolean }[];
}

export interface QuoteRecord {
  schemaVersion: 1;
  // Identity
  runId: string;
  company: string;
  companyId: string;
  profileId: string;
  scenarioId: string;
  timestamp: string; // ISO 8601
  sourceUrl: string;
  formUrl: string;
  // Inputs
  requested: RequestedSettings;
  actual: ActualSelections;
  // Output
  status: QuoteStatus;
  statusDetail: string;
  price: PriceResult;
  terms: Terms;
  evidence: Evidence;
  durationMs: number;
}
