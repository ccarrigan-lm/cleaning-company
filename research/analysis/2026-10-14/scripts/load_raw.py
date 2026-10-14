"""Load every raw harvest CSV (unchanged) into one long table with provenance.

Nothing here alters the raw files. Each row keeps source_file + source_row so any
derived value can be traced back to the exact captured record.
"""
import csv, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HARVEST = ROOT / 'output' / 'harvest'
# Launch27 raw feeds are JSON (git-ignored). Use the project's own output/harvest when present (the Mac copy);
# fall back to the copy staged into the cloud workspace for this audit.
_STAGED = Path('/mnt/user-data/uploads/Documents/Workspace/Projects/cleaning-company/output/harvest')
RAW_FEEDS = HARVEST if any(HARVEST.glob('*/*_raw-feed.json')) else _STAGED
SKIP = re.compile(r'_(form|raw-feed|extras)\.csv$')


def price_files():
    out = {}
    for d in sorted(HARVEST.iterdir()):
        if not d.is_dir() or d.name.startswith('_'):
            continue
        files = sorted(f for f in d.glob('*.csv') if not SKIP.search(f.name))
        if files:
            out[d.name] = files  # all captures, oldest first
    return out


def load_bk_l27():
    frames = []
    for cid, files in price_files().items():
        for f in files:
            df = pd.read_csv(f, dtype=str, keep_default_na=False, encoding='utf-8-sig')
            df.insert(0, 'source_row', range(2, len(df) + 2))  # 1-based incl. header
            df.insert(0, 'source_file', str(f.relative_to(ROOT)))
            df.insert(0, 'company_id', cid)
            df['schema'] = 'bookingkoala' if 'total' in df.columns else 'launch27'
            frames.append(df)
    return pd.concat(frames, ignore_index=True, sort=False).fillna('')


def load_forms():
    rows = {}
    for d in HARVEST.iterdir():
        for f in d.glob('*_form.csv'):
            r = next(csv.DictReader(open(f, encoding='utf-8-sig')))
            r['dims'] = json.loads(r['dims']) if r.get('dims') else []
            rows[d.name] = r
    return rows


def load_feeds():
    feeds = {}
    for f in RAW_FEEDS.glob('*/*_raw-feed.json'):
        cid = f.parent.name
        feeds[cid] = json.load(open(f))[0]
    for f in RAW_FEEDS.glob('_excluded/*/*_raw-feed.json'):
        feeds[f.parent.name.split('-2026')[0]] = json.load(open(f))[0]
    return feeds


def load_runlog():
    return pd.read_csv(HARVEST / '_runs' / '2026-10-14-00-52-02.csv', dtype=str, keep_default_na=False, encoding='utf-8-sig')


def money(s):
    """'$1,234.50' / '505.00' -> 1234.5; blank -> None (never 0)."""
    if s is None or str(s).strip() == '':
        return None
    m = re.search(r'-?[\d,]+(?:\.\d+)?', str(s))
    return float(m.group(0).replace(',', '')) if m else None
