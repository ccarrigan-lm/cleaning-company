"""Build louisville_expected.json: comparison evidence for `npm run validate:louisville`.

Source = the by-hand built-in-browser observations of 14 Oct 2026 (research/validation/2026-10-14/*.json).
These are COMPARISON EVIDENCE for the automated checks, never a substitute for them: an automated check
passes only when the automated run itself observes a price (and, for Launch27, that price equals the
feed calculation made in the same session)."""
import json, re
from pathlib import Path

HERE = Path(__file__).parent
V = HERE / '2026-10-14'
out = {'source': 'research/validation/2026-10-14 (by-hand, built-in browser, 14 Oct 2026)', 'checks': {}}

rf = json.load(open(V / 'red_feather_live.json'))
def rf_key(service, freq, bed, bath, sq):
    return f'{service}|{freq}|{bed}|{bath}|{sq}'
rf_by = {}
for o in rf:
    rf_by.setdefault(rf_key(o['service'], o['frequency'], o['bedrooms'], o['bathrooms'], o['sqft']), o)

RF = []
for b in ['0', '1', '2', '3', '4', '5']:
    RF.append((f'rf-move-bd{b}', 'move: bedrooms vary', 'Move In/Out Clean', 'One-Time', b, '2', '1500-1799 Sq Ft'))
for ba in ['1', '1.5', '2.5', '3', '4']:
    RF.append((f'rf-move-ba{ba}', 'move: bathrooms vary', 'Move In/Out Clean', 'One-Time', '3', ba, '1500-1799 Sq Ft'))
RF += [('rf-same-deep', 'same home, other service', 'Deep Clean', 'One-Time', '3', '2', '1500-1799 Sq Ft'),
       ('rf-same-basic', 'same home, other service', 'Basic Cleaning', 'One-Time', '3', '2', '1500-1799 Sq Ft')]
for b in ['1', '5']:
    RF.append((f'rf-basic-bd{b}', 'basic: bedrooms vary', 'Basic Cleaning', 'One-Time', b, '2', '1500-1799 Sq Ft'))
for ba in ['1', '4']:
    RF.append((f'rf-basic-ba{ba}', 'basic: bathrooms vary', 'Basic Cleaning', 'One-Time', '3', ba, '1500-1799 Sq Ft'))
RF += [('rf-move-sq1000', 'move: sq ft vary', 'Move In/Out Clean', 'One-Time', '3', '2', '1000-1249 Sq Ft'),
       ('rf-move-sq2100', 'move: sq ft vary', 'Move In/Out Clean', 'One-Time', '3', '2', '2100-2399 Sq Ft'),
       ('rf-move-eow', 'move: recurring offered?', 'Move In/Out Clean', 'Every Other Week', '3', '2', '1500-1799 Sq Ft')]
for cid, test, svc, freq, bed, bath, sq in RF:
    h = rf_by.get(rf_key(svc, freq, bed, bath, sq))
    out['checks'][cid] = dict(company='Red Feather Cleaning', test=test, inputs=dict(service=svc, frequency=freq, bedrooms=bed, bathrooms=bath, sqft=sq),
                              byhand_total_before_tax=h['total_before_tax'] if h else None,
                              byhand_frequency_shown=h['frequency_shown'] if h else None,
                              byhand_ts=h['ts'] if h else None)

HOME = {'P1': 'small', 'P5': 'typical', 'P9': 'larger'}
CASE = lambda freq, deep: 'deep' if deep else ('one' if freq.lower().startswith('one') else 'biweekly')
money = lambda s: float(re.search(r'[\d,]+\.\d+', s.replace(',', '')).group(0))
for o in json.load(open(V / 'super_cleaning_live.json')):
    i = o['inputs']
    base = money(re.search(r'BASE PRICE \| (\$[\d.,]+)', o['panel']).group(1))
    sav = money(re.search(r'SAVINGS \| (\$[\d.,]+)', o['panel']).group(1))
    out['checks'][f"l27-super-{HOME[o['home']]}-{CASE(i['frequency'], i['deepExtra'])}"] = dict(company='Super Cleaning Service Louisville', byhand_pretax_first_visit=round(base - sav, 2), byhand_ts=o['ts'])
m2 = json.load(open(V / 'maid2clean_live.json'))
for o in m2['booking_form_observations']:
    i = o['inputs']
    today = money(re.search(r"Today's Total \$([\d.,]+)", o['panel']).group(0))
    out['checks'][f"l27-m2-{HOME[o['home']]}-{CASE(i['frequency'], i['deepExtra'])}"] = dict(company='Maid 2 Clean KY', byhand_pretax_first_visit=today, byhand_ts=o['ts'])
json.dump(out, open(HERE / 'louisville_expected.json', 'w'), indent=1)
miss = [k for k, v in out['checks'].items() if v.get('byhand_total_before_tax', v.get('byhand_pretax_first_visit')) is None]
print(len(out['checks']), 'checks with comparison evidence; missing:', miss)
