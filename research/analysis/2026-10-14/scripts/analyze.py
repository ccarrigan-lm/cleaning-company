"""Comparisons and structure analysis on the audited analytical table.

Fixes the 14 Oct build_market.py lookup bug: a home profile only matches a row whose bedrooms and
bathrooms equal the profile (or where the company's price genuinely does not depend on that
dimension), and whose sq ft band contains the profile's sq ft. No nearest-match, no defaults.
"""
import json, math, re
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / 'data'
ROOT = HERE.parents[2]
M13 = ROOT / 'research' / '2026-10-13'

ana = pd.read_csv(DATA / 'analytical_prices.csv.gz', low_memory=False)
CITY = {c['id']: c for c in json.load(open(ROOT / 'config' / 'cities.json'))['cities']}

PROFILES = [  # realistic Louisville housing mix; sq ft chosen inside common bands, not on band edges
    ('P1', 'Apartment', 1, 1, 750), ('P2', 'Small house', 2, 1, 1000), ('P3', 'Condo / small house', 2, 2, 1200),
    ('P4', 'Starter house', 3, 1.5, 1400), ('P5', 'Typical ranch', 3, 2, 1600), ('P6', 'Typical 2-story', 3, 2, 1900),
    ('P7', 'Larger 3-bed', 3, 2.5, 2200), ('P8', 'Family 4-bed', 4, 2.5, 2500), ('P9', 'Large 4-bed', 4, 3, 3000),
    ('P10', 'Large 5-bed', 5, 3.5, 3800)]
CASES = [('standard', 'one_time'), ('standard', 'weekly'), ('standard', 'biweekly'), ('standard', 'every_4_weeks'),
         ('deep', 'one_time'), ('move_in_out', 'one_time')]

# which dimensions each company's price actually uses (from the analytical rows)
dims = ana.groupby('company_id').agg(has_bed=('bedrooms', lambda s: s.notna().any()), has_bath=('bathrooms', lambda s: s.notna().any()),
                                     has_sq=('sqft_min', lambda s: s.notna().any()))


def lookup(cid, svc, freq, bed, bath, sq):
    d = ana[(ana.company_id == cid) & (ana.service == svc) & (ana.frequency == freq)]
    if d.empty:
        return None, 'service/frequency not offered or not captured'
    hb = d.bedrooms.notna().any()
    hba = d.bathrooms.notna().any()
    hs = d.sqft_min.notna().any()
    m = d
    if hb:
        m = m[m.bedrooms == bed]
    if hba:
        m = m[m.bathrooms == bath]
    if hs:
        m = m[(m.sqft_min <= sq) & (m.sqft_max.fillna(np.inf) >= sq)]
    if m.empty:
        return None, 'no exact bed/bath/sq ft match on this company\'s form'
    prices = m.price_first_or_per_visit.unique()
    ong = m.price_ongoing_visit.dropna().unique()
    if len(prices) > 1:
        # same size selects but different non-size options (e.g. MIA duplicate sq ft label) - report range
        return dict(first=float(np.min(prices)), first_max=float(np.max(prices)), ongoing=float(np.min(ong)) if len(ong) else np.nan,
                    n=len(m), note='several captured prices for this profile; lowest shown', row=m.iloc[0]), ''
    r = m.iloc[0]
    note = []
    if not hb:
        note.append('price does not vary by bedrooms')
    if not hba:
        note.append('price does not vary by bathrooms')
    if not hs:
        note.append('price does not vary by sq ft')
    return dict(first=float(prices[0]), first_max=float(prices[0]), ongoing=float(ong[0]) if len(ong) else np.nan, n=len(m), note='; '.join(note), row=r), ''


def profile_table(company_ids):
    out = []
    for cid in company_ids:
        for pid, plabel, bed, bath, sq in PROFILES:
            for svc, freq in CASES:
                hit, why = lookup(cid, svc, freq, bed, bath, sq)
                base = dict(company_id=cid, profile=pid, profile_label=f'{plabel}: {bed} bd / {bath:g} ba / {sq:,} sq ft', bedrooms=bed, bathrooms=bath,
                            sqft=sq, service=svc, frequency=freq)
                if hit is None:
                    out.append({**base, 'first_visit_pretax': np.nan, 'ongoing_visit_pretax': np.nan, 'status': why})
                    continue
                r = hit['row']
                out.append({**base, 'company': r.company, 'city': r.city, 'evidence_tier': r.evidence_tier,
                            'first_visit_pretax': hit['first'], 'first_visit_max': hit['first_max'], 'ongoing_visit_pretax': hit['ongoing'],
                            'recurring_basis': r.recurring_basis, 'price_basis': r.price_basis, 'matched_site_service': r.site_service,
                            'matched_sqft_label': r.sqft_label, 'status': 'priced' + (f" ({hit['note']})" if hit['note'] else ''),
                            'source_file': r.source_file, 'source_row': int(r.source_row)})
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- Louisville models (13 Oct) outside the harvest
def louisville_models():
    """MIA deep/move (live add-on checks), R&R formula, Cleanoria published ranges, Stitch published list."""
    fm = pd.read_csv(M13 / 'full_matrix.csv')
    rr = json.load(open(M13 / 'rr_maids_model.json'))
    cl = json.load(open(M13 / 'cleanoria_model.json'))
    STITCH = {(1, 1): 150, (1, 2): 180, (2, 1): 170, (2, 2): 180, (2, 3): 210, (3, 1): 180, (3, 2): 220, (3, 3): 265, (3, 4): 300,
              (4, 1): 250, (4, 2): 250, (4, 3): 290, (4, 4): 330, (4, 5): 370, (5, 1): 280, (5, 2): 280, (5, 3): 340, (5, 4): 370, (5, 5): 400}
    RR = {(2, 2): '2 Bed / 2 Bath', (3, 1): '3 Bed / 1 Bath', (3, 2): '3 Bed / 2 Bath', (4, 2): '4 Bed / 2 Bath', (4, 2.5): '4 Bed / 2.5 Bath',
          (4, 3): '4 Bed / 3 Bath', (4, 3.5): '4 Bed / 3.5 Bath', (5, 3.5): '5 Bed / 3.5 Bath', (5, 4): '5 Bed / 4 Bath', (5, 5): '5 Bed / 5 Bath'}
    rows = []
    ma = fm[(fm.company == 'Maids in Apron') & fm.service.isin(['deep', 'move_in_out'])]
    for pid, plabel, bed, bath, sq in PROFILES:
        lab = f'{plabel}: {bed} bd / {bath:g} ba / {sq:,} sq ft'
        base = dict(profile=pid, profile_label=lab, bedrooms=bed, bathrooms=bath, sqft=sq, frequency='one_time')
        # MIA deep / move: standard first visit + bedroom-based add-on (13 Oct live captures incl. add-on checks)
        for svc in ['deep', 'move_in_out']:
            m = ma[(ma.service == svc) & (ma.bedrooms == bed) & (ma.bathrooms == bath)]
            m = m[[(lambda a, b: a <= sq <= b)(*map(int, s.replace(' ', '').split('-'))) if s.replace(' ', '').split('-')[-1].isdigit() else False for s in m.sqft_range]]
            rows.append({**base, 'company_id': 'maids-in-apron', 'company': 'Maids in Apron', 'city': 'louisville', 'service': svc,
                         'evidence_tier': 'reconstructed model from 13 Oct live captures (add-on checked live; additive fit exact)',
                         'first_visit_pretax': float(m.first_visit_pretax.iloc[0]) if len(m) else np.nan, 'ongoing_visit_pretax': np.nan,
                         'status': 'priced' if len(m) else 'no exact match', 'source_file': 'research/2026-10-13/full_matrix.csv + maids_in_apron_model.json'})
        # R&R: first clean only, average condition, 1 story, no basement
        lay = RR.get((bed, bath))
        sqh = None
        for labh, h in rr['sqft_hours'].items():
            a, b = (0, 999) if 'less' in labh else map(int, labh.split('-'))
            if a <= sq <= b:
                sqh = h
        for svc, key in [('standard', '1st Time Basic Cleaning'), ('deep', '1st Time Deep Cleaning')]:
            v = (rr['bed_bath_hours'][lay] + sqh + rr['cleaning_type_hours'][key]) * rr['hourly_rate'] if lay and sqh is not None else np.nan
            rows.append({**base, 'company_id': 'rr-maids', 'company': 'Rocking Robins (R&R) Maids', 'city': 'louisville', 'service': svc,
                         'evidence_tier': 'reconstructed calculator formula (13 Oct; 1 combination checked live)',
                         'first_visit_pretax': v, 'ongoing_visit_pretax': np.nan,
                         'status': 'priced (first clean only; average condition, 1 story, no basement)' if not np.isnan(v) else
                                   ('layout not offered (smallest is 2 bd / 2 ba)' if not lay else 'sq ft band gap in calculator'),
                         'source_file': 'research/2026-10-13/rr_maids_model.json'})
        # Cleanoria: published Thumbtack range (low-high); midpoint is NOT a quote
        for svc, k in [('standard', 'standard'), ('deep', 'deep')]:
            lo = hi = np.nan
            for band, tab in cl[k].items():
                a, b = map(int, band.split('-'))
                if a <= sq <= b and f'{bed}/{bath:g}' in tab:
                    lo, hi = tab[f'{bed}/{bath:g}']
            rows.append({**base, 'company_id': 'cleanoria', 'company': 'Cleanoria (Thumbtack)', 'city': 'louisville', 'service': svc,
                         'evidence_tier': 'published price range (Thumbtack FAQ, 13 Oct)', 'first_visit_pretax': lo, 'first_visit_max': hi,
                         'ongoing_visit_pretax': np.nan, 'status': 'published range' if not np.isnan(lo) else 'layout not in published table',
                         'source_file': 'research/2026-10-13/cleanoria_model.json'})
        st = STITCH.get((bed, int(math.floor(bath))))
        rows.append({**base, 'company_id': 'stitch', 'company': 'Stitch Cleaning', 'city': 'louisville', 'service': 'standard',
                     'evidence_tier': 'published price list (13 Oct; whole baths only, no sq ft)', 'first_visit_pretax': st if st else np.nan,
                     'ongoing_visit_pretax': np.nan, 'status': ('published list' + (' (half bath not priced; whole-bath price used)' if bath % 1 else '')) if st else 'layout not listed',
                     'source_file': 'research/2026-10-13/build.py (STITCH table) / stitchcleaning.com pricing page'})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- structure metrics
REF = (3, 2, 1700)


def structure(cid):
    def p(svc, freq, bed, bath, sq, ongoing=False):
        h, _ = lookup(cid, svc, freq, bed, bath, sq)
        if h is None:
            return np.nan
        return h['ongoing'] if ongoing else h['first']
    b = p('standard', 'one_time', *REF)
    r = dict(company_id=cid, ref_home='3 bd / 2 ba / 1,700 sq ft', std_one_time=b)
    r['add_bedroom_3to4'] = p('standard', 'one_time', 4, 2, 1700) - b
    r['add_full_bath_2to3'] = p('standard', 'one_time', 3, 3, 1700) - b
    r['add_half_bath_2to2.5'] = p('standard', 'one_time', 3, 2.5, 1700) - b
    r['add_1000_sqft_1700to2700'] = p('standard', 'one_time', 3, 2, 2700) - b
    for f in ['weekly', 'biweekly', 'every_4_weeks']:
        f1, fo = p('standard', f, *REF), p('standard', f, *REF, ongoing=True)
        r[f'{f}_first_visit_disc'] = 1 - f1 / b if b and not np.isnan(f1) else np.nan
        r[f'{f}_ongoing_disc'] = 1 - fo / b if b and not np.isnan(fo) else np.nan
    for s in ['deep', 'move_in_out']:
        v = p(s, 'one_time', *REF)
        r[f'{s}_x_standard'] = v / b if b and not np.isnan(v) else np.nan
        r[f'{s}_one_time'] = v
    rows = ana[ana.company_id == cid]
    # which size inputs actually move the price (holding the other inputs fixed), standard one-time if available
    std = rows[(rows.service == 'standard')]
    std = std[std.frequency == ('one_time' if (std.frequency == 'one_time').any() else std.frequency.mode().iloc[0])] if len(std) else rows
    def varies(col, others):
        """True if changing `col` alone changes the price for some fixed combination of the other inputs."""
        if std[col].isna().all():
            return None
        keys = [c for c in others if std[c].notna().any()]
        groups = std.groupby(keys, dropna=False) if keys else [(None, std)]
        return any(g.groupby(col).price_first_or_per_visit.first().nunique() > 1 for _, g in groups)
    vb, va, vs = varies('bedrooms', ['bathrooms', 'sqft_min']), varies('bathrooms', ['bedrooms', 'sqft_min']), varies('sqft_min', ['bedrooms', 'bathrooms'])
    r['price_varies_by'] = ' + '.join(x for x, ok in [('bedrooms', vb), ('bathrooms', va), ('sq ft', vs)] if ok) or 'none of bed/bath/sq ft'
    r['inputs_collected_but_not_priced'] = ', '.join(x for x, ok in [('bedrooms', vb), ('bathrooms', va), ('sq ft', vs)] if ok is False)
    r['services_captured'] = ', '.join(sorted(rows.service.unique()))
    r['frequencies_captured'] = ', '.join(sorted(rows.frequency.unique()))
    r['analytical_rows'] = len(rows)
    return r


def main():
    cids = sorted(ana.company_id.unique())
    prof = profile_table(cids)
    lv = louisville_models()
    prof_all = pd.concat([prof, lv], ignore_index=True, sort=False)
    prof_all['city'] = prof_all.city.fillna(prof_all.company_id.map(ana.groupby('company_id').city.first()))
    prof_all['company'] = prof_all.company.fillna(prof_all.company_id.map(ana.groupby('company_id').company.first()))
    prof_all.to_csv(DATA / 'profile_prices_all.csv', index=False)
    st = pd.DataFrame([structure(c) for c in cids])
    st.insert(1, 'company', st.company_id.map(ana.groupby('company_id').company.first()))
    st.insert(2, 'city', st.company_id.map(ana.groupby('company_id').city.first()))
    st.to_csv(DATA / 'structure_by_company.csv', index=False)
    print(prof_all.status.str.split(' \\(').str[0].value_counts().to_string())
    print(st[['company', 'city', 'std_one_time', 'add_bedroom_3to4', 'add_full_bath_2to3', 'add_1000_sqft_1700to2700', 'biweekly_ongoing_disc', 'deep_x_standard']].round(2).to_string())


if __name__ == '__main__':
    main()
