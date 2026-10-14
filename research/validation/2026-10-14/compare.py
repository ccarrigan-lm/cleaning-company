"""Compare live-form observations (14 Oct, built-in browser) with feed calculations and the 14 Oct harvest."""
import csv, json, re
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
FEED_SUPER = ROOT / 'output' / 'harvest' / 'super-cleaning-louisville' / '2026-10-14-00-52-02.csv'
RF_HARVEST = ROOT / 'output' / 'harvest' / 'redfeathercleaning' / '2026-10-14-00-52-02_zip40217.csv'
money = lambda s: float(re.search(r'[\d,]+\.\d+|\d+', s.replace(',', '')).group(0))
rows = []

# ---- Super Cleaning: live vs harvested Launch27 feed rows
feed = list(csv.DictReader(open(FEED_SUPER, encoding='utf-8-sig')))
FMAP = {'One Time': 'One Time', 'Every 2 Weeks (Save 25%)': 'Every 2 Weeks (Save 25%)'}
for o in json.load(open(HERE / 'super_cleaning_live.json')):
    i = o['inputs']
    p = o['panel']
    base = money(re.search(r'BASE PRICE \| (\$[\d.,]+)', p).group(1))
    sav = money(re.search(r'SAVINGS \| (\$[\d.,]+)', p).group(1)) if 'SAVINGS' in p else 0.0
    tax = money(re.search(r'SALES TAX \| (\$[\d.,]+)', p).group(1))
    tot = money(re.search(r'TOTAL \| (\$[\d.,]+)', p).group(1))
    fb = re.match(r'(\d+)', i['baths']).group(1)
    hb = re.match(r'(\d+)', i['halfBaths']).group(1)
    addon = [r for r in feed if r['service'] == i['service'] and r['frequency'] == FMAP[i['frequency']] and r['sqft'] == i['sqft']
             and r['fullBaths'] == fb and r['halfBaths'] == hb and (('Deep' in r['addOn']) if i['deepExtra'] else r['addOn'] == '')]
    calc = float(addon[0]['firstVisitPreTax']) if addon else None
    pre = round(base - sav, 2)
    rows.append(dict(company='Super Cleaning Service Louisville', home=o['home'], selection=f"{i['service']}; {i['sqft']}; {i['baths']}; {i['halfBaths']}; {i['frequency']}" + ('; + Deep Cleaning' if i['deepExtra'] else ''),
                     live_pretax_first_visit=pre, live_tax=tax, live_tax_pct=round(tax / pre * 100, 2) if pre else None, live_total=tot,
                     live_recurring_note='single booking total; discount applied to this (first) visit; no separate recurring line',
                     calculated_pretax=calc, calc_source='Launch27 feed (harvest row)', difference=None if calc is None else round(pre - calc, 2),
                     match='yes' if calc is not None and abs(pre - calc) < 0.005 else 'NO', observed_at=o['ts'], url=o['url'],
                     evidence='research/validation/2026-10-14/super_cleaning_live.json'))

# ---- Maid 2 Clean: live booking form vs its own feed (computed here from the saved feed summary)
m2 = json.load(open(HERE / 'maid2clean_live.json'))
svc = {s['name']: s for s in m2['feed_summary']['services']}
deep = next(e for e in m2['feed_summary']['extras_all_bedroom_services'] if e['name'].startswith('Deep'))['price']
for o in m2['booking_form_observations']:
    i = o['inputs']
    s = svc[i['service']]
    calc = s['price']
    for prm in s['params']:
        if prm['type'] == 'flat':
            calc += prm['price'] * int(re.match(r'\d+', i['baths']).group(0))
        else:
            calc += next(r['price'] for r in prm['ranges'] if r['label'] == i['sqft'])
    if i['deepExtra']:
        calc += deep
    p = o['panel']
    today = money(re.search(r"Today's Total \$([\d.,]+)", p).group(1))
    rec = money(re.search(r'Recurring Cleaning Price \$([\d.,]+)', p).group(1))
    rows.append(dict(company='Maid 2 Clean KY', home=o['home'], selection='; '.join(str(v) for v in i.values()),
                     live_pretax_first_visit=today, live_tax=0.0, live_tax_pct=0.0, live_total=money(re.search(r'TOTAL \$([\d.,]+)', p).group(1)),
                     live_recurring_note=(f'recurring visit ${rec:.2f} (shown separately)' if i['frequency'] != 'One Time' else 'one-time'),
                     calculated_pretax=calc, calc_source='Launch27 feed (smilesaremaid.launch27.com)', difference=round(today - calc, 2),
                     match='yes' if abs(today - calc) < 0.005 else 'NO', observed_at=o['ts'], url=m2['booking_form_url'],
                     evidence='research/validation/2026-10-14/maid2clean_live.json'))

# ---- Red Feather: live re-capture vs 14 Oct harvest
hv = list(csv.DictReader(open(RF_HARVEST, encoding='utf-8-sig')))
for o in json.load(open(HERE / 'red_feather_live.json')):
    h = [r for r in hv if r['service'] == o['service_shown'] and r['frequency'] == o['frequency_shown'] and r['bedrooms'] == o['bedrooms']
         and r['bathrooms'] == o['bathrooms'] and r['sqft'] == o['sqft']]
    hp = money(h[0]['totalBeforeTax']) if h else None
    rows.append(dict(company='Red Feather Cleaning', home=o['test'], selection=f"{o['service_shown']}; {o['frequency']} requested -> {o['frequency_shown']} shown; {o['bedrooms']} bd; {o['bathrooms']} ba; {o['sqft']}",
                     live_pretax_first_visit=o['total_before_tax'], live_tax=round(o['total_incl_tax'] - o['total_before_tax'], 2),
                     live_tax_pct=round((o['total_incl_tax'] / o['total_before_tax'] - 1) * 100, 2), live_total=o['total_incl_tax'],
                     live_recurring_note='', calculated_pretax=hp, calc_source='14 Oct harvest row (live form, earlier capture)' + ('' if not h else f" verified={h[0]['verified']}"),
                     difference=None if hp is None else round(o['total_before_tax'] - hp, 2), match='yes' if hp is not None and abs(o['total_before_tax'] - hp) < 0.005 else ('no harvest row' if hp is None else 'NO'),
                     observed_at=o['ts'], url=o['url'], evidence='research/validation/2026-10-14/red_feather_live.json'))

with open(HERE / 'validation_results.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print(Counter((r['company'], r['match']) for r in rows))
for r in rows:
    if r['match'] != 'yes':
        print(r['company'], r['home'], r['selection'], r['live_pretax_first_visit'], r['calculated_pretax'], r['match'])
