#!/usr/bin/env bash
# Rebuild every derived output in research/analysis/2026-10-14 from the raw captures (no web access).
set -euo pipefail
cd "$(dirname "$0")"
python3 normalize.py
python3 analyze.py
python3 five_company_basis.py
python3 build_tables.py
python3 build_workbook.py
echo "Recalculate formulas: open the workbook in Excel/LibreOffice (or run the xlsx recalc script)."
