# Audit and analysis, 14 Oct 2026

This folder audits the 13–14 Oct price collection and analyses it for a Louisville pricing decision. It supersedes `research/market/2026-10-14/`, which has a profile-lookup bug and mislabelled evidence (see `AUDIT_REPORT.md`, issues A1 and A2). Raw captures and the older snapshots are unchanged.

Start with:
1. `FINDINGS.md`: what the data supports, what it doesn't, and the cost inputs still needed.
2. `Louisville_Comparison_Validated.xlsx`: comparison tables with evidence tiers, source rows, issues, rules and a data dictionary.
3. `AUDIT_REPORT.md`: coverage, issues, corrections and open verification items.

## Data files (`data/`)

| File | Rows | Notes |
|---|---|---|
| `observations_normalized.csv.gz` | 294,901 | Every raw row, normalized; `include`, `flags` (R1–R10), `source_file`, `source_row` |
| `analytical_prices.csv.gz` | 171,247 | Included rows with duplicates collapsed |
| `profile_prices_all.csv` | 10 profiles × 6 cases × company | Harvested companies plus 13 Oct Louisville models and published lists |
| `structure_by_company.csv` | 27 | Price-change metrics per usable company |
| `companies.csv` | 45 | Registry: identity, city evidence, evidence tier, capture status |
| `price_availability.csv` | 183 | Price-availability category per site; "unknown / unreviewed" does not mean hidden |
| `city_coverage.csv`, `extras.csv`, `scope.csv`, `rule_counts.csv` | | Supporting tables |
| `old_profiles_recheck.csv` | 2,196 | Every 14 Oct profile value rechecked with the corrected lookup |

## Rebuild

```bash
bash scripts/run_all.sh      # about 2.5 minutes; reads output/harvest/ only, no web access
```

Needs Python 3 with pandas and openpyxl. Open the workbook in Excel or LibreOffice to recalculate its formulas. The Launch27 raw feeds (`*_raw-feed.json`) are git-ignored and exist only in the Mac copy of `output/harvest/`.
