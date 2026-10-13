"""Build the Louisville cleaning price matrix from captured competitor pricing models."""
import json, csv, itertools, math, statistics as st
from pathlib import Path

D = Path(__file__).parent
TAX = 0.06
sl = json.load(open(D / 'scrub_lou_model.json'))
ma = json.load(open(D / 'maids_in_apron_model.json'))
sc = json.load(open(D / 'super_cleaning_model.json'))

def rng(label):
    """'1000-1499' -> (1000,1499); '7001+' -> (7001, 99999)"""
    s = label.replace(' ', '').replace('sqft', '').split('(')[0]
    if s.endswith('+') or s.endswith('-'):
        return int(s.rstrip('+-')), 99999
    a, b = s.split('-')
    return int(a), int(b)

def bucket(labels, sqft):
    for i, l in enumerate(labels):
        a, b = rng(l)
        if a <= sqft <= b:
            return i
    return None

r2 = lambda x: None if x is None else round(x + 1e-9, 2)

# ---------------- Full native matrices (every combination each site offers) ----------------
full = []

# Scrub Lou: per-visit price = (sqft_base + bed_add + bath_add) * freq_mult. Same price every visit.
SL_FREQ = {'One-Time': 'one_time', 'Weekly': 'weekly', 'Every Other Week': 'biweekly', 'Every 4 Weeks': 'every_4_weeks'}
SL_SVC = {'Routine Cleaning': 'standard', 'Deep Clean': 'deep', 'Move-In/Move-Out Cleaning': 'move_in_out'}
for svc, sv in sl['services'].items():
    for f, mult in sl['frequency_multiplier'].items():
        for bi, bed in enumerate(sl['bedrooms']):
            for ba_i, bath in enumerate(sl['bathrooms']):
                for si, sq in enumerate(sv['sqft']):
                    pre = (sv['sqft_base'][si] + sl['bedroom_add'][bi] + sl['bathroom_add'][ba_i]) * mult
                    full.append(dict(company='Scrub Lou', service=SL_SVC[svc], site_service=svc, frequency=SL_FREQ[f],
                                     bedrooms=bed, bathrooms=bath, sqft_range=sq,
                                     first_visit_pretax=r2(pre), recurring_visit_pretax=r2(pre) if f != 'One-Time' else None,
                                     method='live form capture (5,220 combos) + exact additive fit'))

# Maids in Apron: first visit full price; recurring = base - flat (or -5% twice a week).
MA_REC = {'One-Time': None, 'Weekly': ('flat', 20), 'Every Other Week': ('flat', 15), 'Every 4 Weeks': ('flat', 10)}
MA_FREQ = {'One-Time': 'one_time', 'Weekly': 'weekly', 'Every Other Week': 'biweekly', 'Every 4 Weeks': 'every_4_weeks'}
ma_sq = [s for s in ma['sqft'] if 'duplicate' not in s]
ma_sq_base = [b for s, b in zip(ma['sqft'], ma['sqft_base']) if 'duplicate' not in s]
for svc in ['standard', 'deep', 'move_in_out']:
    for f, rec in MA_REC.items():
        if svc != 'standard' and f != 'One-Time':
            continue
        for bi, bed in enumerate(ma['bedrooms']):
            for ba_i, bath in enumerate(ma['bathrooms']):
                for si, sq in enumerate(ma_sq):
                    base = ma_sq_base[si] + ma['bedroom_add'][bi] + ma['bathroom_add'][ba_i]
                    add = 0
                    if svc == 'deep':
                        add = ma['deep_clean_addon_by_bedrooms'][str(bed)]
                    if svc == 'move_in_out':
                        add = ma['move_in_out_addon_by_bedrooms'][str(bed)]
                    first = base + add
                    recv = None if rec is None else base - rec[1]
                    full.append(dict(company='Maids in Apron', service=svc,
                                     site_service='Flat rate' + ('' if svc == 'standard' else (' + Deep Cleaning' if svc == 'deep' else ' + Move In Out')),
                                     frequency=MA_FREQ[f], bedrooms=bed, bathrooms=bath, sqft_range=sq,
                                     first_visit_pretax=r2(first), recurring_visit_pretax=r2(recv),
                                     method='live form capture (7,056 base combos + add-on checks) + exact additive fit'))

# Super Cleaning: base = bedroom base + sqft add + 35*full + 20*half; % off applies to every visit incl. first.
SC_FREQ = {'One Time': 'one_time', 'Every Week': 'weekly', 'Every 2 Weeks': 'biweekly', 'Every 4 Weeks': 'every_4_weeks'}
for svc in ['standard', 'deep', 'move_in_out']:
    for f, pct in sc['frequency_discount_pct'].items():
        if svc != 'standard' and f != 'One Time':
            continue
        m = 1 - pct / 100
        for bed, bb in sc['bedroom_base'].items():
            for full_b in range(0, 7):
                for half_b in range(0, 3):
                    bath = full_b + 0.5 * half_b
                    if bath == 0:
                        continue
                    for si, sq in enumerate(sc['sqft']):
                        base = bb + sc['sqft_add'][si] + 35 * full_b + 20 * half_b
                        add = 0
                        if svc == 'deep':
                            add = sc['deep_clean_addon_first_visit'][bed]
                        if svc == 'move_in_out':
                            add = sc['move_in_out_addon'][bed]
                        full.append(dict(company='Super Cleaning Service', service=svc,
                                         site_service=f'{bed} Bedroom Home' + ('' if svc == 'standard' else (' + Deep Cleaning' if svc == 'deep' else ' + Move In/Out')),
                                         frequency=SC_FREQ[f], bedrooms=int(bed), bathrooms=bath, sqft_range=sq,
                                         full_baths=full_b, half_baths=half_b,
                                         first_visit_pretax=r2((base + add) * m), recurring_visit_pretax=r2(base * m) if pct else None,
                                         method="site's own price feed + live spot checks"))

for row in full:
    row['first_visit_with_tax'] = r2(row['first_visit_pretax'] * (1 + TAX))

# ---------------- Common home profiles for apples-to-apples comparison ----------------
STITCH = {  # published flat one-time standard prices by bed / bath (https://stitchcleaning.com/louisville-cleaning-services-pricing/)
    (1, 1): 150, (1, 2): 180, (2, 1): 170, (2, 2): 180, (2, 3): 210, (3, 1): 180, (3, 2): 220, (3, 3): 265, (3, 4): 300,
    (4, 1): 250, (4, 2): 250, (4, 3): 290, (4, 4): 330, (4, 5): 370, (5, 1): 280, (5, 2): 280, (5, 3): 340, (5, 4): 370, (5, 5): 400}

def stitch(bed, bath):
    b = int(math.floor(bath))  # Stitch lists whole baths; half baths not priced separately
    for bb in range(b, 0, -1):
        if (bed, bb) in STITCH:
            return STITCH[(bed, bb)]
    return None

PROFILES = []
for bed, bath, sqft in [
    (1, 1, 700), (1, 1, 900), (2, 1, 1000), (2, 1.5, 1100), (2, 2, 1200), (3, 1, 1250), (3, 1.5, 1400), (3, 2, 1600),
    (3, 2, 1800), (3, 2.5, 2000), (3, 3, 2200), (4, 2, 2000), (4, 2.5, 2300), (4, 3, 2700), (4, 3.5, 3200),
    (5, 3, 3000), (5, 3.5, 3600), (5, 4, 4200), (5, 4.5, 4800)]:
    PROFILES.append((bed, bath, sqft))

def price_sl(svc, freq, bed, bath, sqft):
    name = {'standard': 'Routine Cleaning', 'deep': 'Deep Clean', 'move_in_out': 'Move-In/Move-Out Cleaning'}[svc]
    sv = sl['services'][name]
    si = bucket(sv['sqft'], sqft)
    if si is None or bed not in sl['bedrooms'] or bath not in sl['bathrooms']:
        return None, None, 'outside online options'
    mult = {'one_time': 1, 'weekly': .8, 'biweekly': .85, 'every_4_weeks': 1}[freq]
    p = (sv['sqft_base'][si] + sl['bedroom_add'][sl['bedrooms'].index(bed)] + sl['bathroom_add'][sl['bathrooms'].index(bath)]) * mult
    return r2(p), (r2(p) if freq != 'one_time' else None), sv['sqft'][si]

def price_ma(svc, freq, bed, bath, sqft):
    si = bucket(ma_sq, sqft)
    base = ma_sq_base[si] + ma['bedroom_add'][ma['bedrooms'].index(bed)] + ma['bathroom_add'][ma['bathrooms'].index(bath)]
    add = {'standard': 0, 'deep': ma['deep_clean_addon_by_bedrooms'][str(bed)], 'move_in_out': ma['move_in_out_addon_by_bedrooms'][str(bed)]}[svc]
    rec = {'one_time': None, 'weekly': 20, 'biweekly': 15, 'every_4_weeks': 10}[freq]
    return r2(base + add), (None if rec is None else r2(base - rec)), ma_sq[si]

def price_sc(svc, freq, bed, bath, sqft):
    full_b, half_b = int(bath), int(round((bath % 1) * 2))
    si = bucket(sc['sqft'], sqft)
    base = sc['bedroom_base'][str(bed)] + sc['sqft_add'][si] + 35 * full_b + 20 * half_b
    add = {'standard': 0, 'deep': sc['deep_clean_addon_first_visit'][str(bed)], 'move_in_out': sc['move_in_out_addon'][str(bed)]}[svc]
    m = 1 - {'one_time': 0, 'weekly': .35, 'biweekly': .25, 'every_4_weeks': .10}[freq]
    return r2((base + add) * m), (None if freq == 'one_time' else r2(base * m)), sc['sqft'][si]

rr = json.load(open(D / 'rr_maids_model.json'))
cl = json.load(open(D / 'cleanoria_model.json'))
RR_LAYOUT = {(2, 2): '2 Bed / 2 Bath', (3, 1): '3 Bed / 1 Bath', (3, 2): '3 Bed / 2 Bath', (4, 2): '4 Bed / 2 Bath', (4, 2.5): '4 Bed / 2.5 Bath',
             (4, 3): '4 Bed / 3 Bath', (4, 3.5): '4 Bed / 3.5 Bath', (5, 3.5): '5 Bed / 3.5 Bath', (5, 4): '5 Bed / 4 Bath', (5, 5): '5 Bed / 5 Bath'}

def price_rr(svc, freq, bed, bath, sqft):
    # First clean only (frequency does not change the online price); average condition, 1 story, no basement.
    if svc == 'move_in_out' or freq != 'one_time' or (bed, bath) not in RR_LAYOUT:
        return None, None, None
    sq = None
    for lab, h in rr['sqft_hours'].items():
        a, b = (0, 999) if 'less' in lab else map(int, lab.split('-'))
        if a <= sqft <= b:
            sq = (lab, h)
    if sq is None:
        return None, None, None
    hrs = rr['bed_bath_hours'][RR_LAYOUT[(bed, bath)]] + sq[1] + rr['cleaning_type_hours']['1st Time Deep Cleaning' if svc == 'deep' else '1st Time Basic Cleaning']
    return r2(hrs * rr['hourly_rate']), None, sq[0]

def price_cl(svc, freq, bed, bath, sqft):
    if svc == 'move_in_out' or freq != 'one_time':
        return None, None, None
    for band, rows in cl['standard' if svc == 'standard' else 'deep'].items():
        a, b = map(int, band.split('-'))
        if a <= sqft <= b:
            v = rows.get(f'{bed}/{bath:g}')
            return (r2(sum(v) / 2), None, band) if v else (None, None, None)
    return None, None, None

COMP = [('Scrub Lou', price_sl), ('Maids in Apron', price_ma), ('Super Cleaning Service', price_sc),
        ('Rocking Robins (R&R) Maids', price_rr), ('Cleanoria (Thumbtack midpoint)', price_cl)]
comparison = []
for (bed, bath, sqft), svc, freq in itertools.product(PROFILES, ['standard', 'deep', 'move_in_out'],
                                                      ['one_time', 'weekly', 'biweekly', 'every_4_weeks']):
    if svc != 'standard' and freq != 'one_time':
        continue
    row = dict(profile=f'{bed} bd / {bath:g} ba / {sqft:,} sq ft', bedrooms=bed, bathrooms=bath, sqft=sqft, service=svc, frequency=freq)
    firsts, recs = [], []
    for name, fn in COMP:
        f, r, b = fn(svc, freq, bed, bath, sqft)
        row[f'{name} first visit'] = f
        row[f'{name} recurring visit'] = r
        if f is not None:
            firsts.append(f)
        if r is not None:
            recs.append(r)
    stv = stitch(bed, bath) if (svc == 'standard' and freq == 'one_time') else None
    row['Stitch Cleaning (published, one-time)'] = stv
    pool = firsts + ([stv] if stv else [])
    row['market low'] = min(pool)
    row['market median'] = r2(st.median(pool))
    row['market high'] = max(pool)
    row['market avg'] = r2(st.mean(pool))
    if recs:
        row['recurring median'] = r2(st.median(recs))
    comparison.append(row)

# ---------------- Fit an additive "market median" formula for standard one-time ----------------
import numpy as np
std = [c for c in comparison if c['service'] == 'standard' and c['frequency'] == 'one_time']
X = np.array([[1, c['bedrooms'], c['bathrooms'], c['sqft'] / 1000] for c in std])
y = np.array([c['market median'] for c in std])
coef, *_ = np.linalg.lstsq(X, y, rcond=None)
pred = X @ coef
fit = dict(intercept=round(coef[0], 2), per_bedroom=round(coef[1], 2), per_bathroom=round(coef[2], 2), per_1000_sqft=round(coef[3], 2),
           mean_abs_error=round(float(np.mean(np.abs(pred - y))), 2), r2=round(float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3))

# Deep / move premiums over standard (median across companies)
prem = {}
for svc in ['deep', 'move_in_out']:
    ratios = []
    for p in PROFILES:
        s = next(c for c in comparison if c['service'] == 'standard' and c['frequency'] == 'one_time' and (c['bedrooms'], c['bathrooms'], c['sqft']) == p)
        d = next(c for c in comparison if c['service'] == svc and (c['bedrooms'], c['bathrooms'], c['sqft']) == p)
        for name, _ in COMP[:3]:
            if s[f'{name} first visit'] and d[f'{name} first visit']:
                ratios.append(d[f'{name} first visit'] / s[f'{name} first visit'])
    prem[svc] = dict(median_multiple=round(st.median(ratios), 2), low=round(min(ratios), 2), high=round(max(ratios), 2))

json.dump(dict(full=full, comparison=comparison, fit=fit, premiums=prem), open(D / 'matrix.json', 'w'), default=float)
with open(D / 'full_matrix.csv', 'w', newline='') as fh:
    keys = ['company', 'service', 'site_service', 'frequency', 'bedrooms', 'bathrooms', 'full_baths', 'half_baths', 'sqft_range',
            'first_visit_pretax', 'recurring_visit_pretax', 'first_visit_with_tax', 'method']
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    for r in full:
        w.writerow({k: r.get(k, '') for k in keys})
print(len(full), 'native rows;', len(comparison), 'comparison rows')
print('fit', fit)
print('premiums', prem)
