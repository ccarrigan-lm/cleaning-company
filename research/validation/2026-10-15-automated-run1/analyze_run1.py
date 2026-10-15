"""Derive per-check statuses for automated run 2026-10-15-13-48-53 (original files untouched, in ./original).

Two views of the Red Feather checks are kept apart:
  * as_reported  - what the validator itself recorded (prices null -> inconclusive; its "sq ft: false" etc. are invalid)
  * reparsed     - prices re-read from THIS run's own saved Booking Summary text (the "$" was an icon-font glyph U+F155)
The 14 Oct by-hand observations are comparison evidence only."""
import csv, json, re
from pathlib import Path

HERE = Path(__file__).parent
R = json.load(open(HERE / 'original' / 'results.json'))
EXP = json.load(open(HERE.parent / 'louisville_expected.json'))['checks']
RF_IDS = (['rf-move-bd' + b for b in '012345'] + ['rf-move-ba' + b for b in ['1', '1.5', '2.5', '3', '4']] +
          ['rf-same-deep', 'rf-same-basic', 'rf-basic-bd1', 'rf-basic-bd5', 'rf-basic-ba1', 'rf-basic-ba4', 'rf-move-sq1000', 'rf-move-sq2100', 'rf-move-eow'])
money = lambda s, lab: (lambda m: float(m.group(1).replace(',', '')) if m else None)(re.search(lab + r'\s*\D{0,3}?\s*([\d,]+\.\d\d)', s))
rows = []
rf = [r for r in R['results'] if r['company'] == 'Red Feather Cleaning']
assert len(rf) == 20
for cid, r in zip(RF_IDS, rf):
    s, i = r['summaryText'], r['inputs']
    shown = {k: (re.search(p, s) or [None, None])[1] for k, p in dict(service=r'Service (.*?) Frequency', frequency=r'Frequency (.*?) Bedrooms', bedrooms=r'Bedrooms (\S+)', bathrooms=r'Bathrooms (\S+)', sqft=r'Sq Ft (.*? Sq Ft)').items()}
    sel_ok = all(shown[k] == i[k] for k in ['service', 'bedrooms', 'bathrooms', 'sqft'])
    pre = money(s, 'Total Before Tax'); tot = money(s, 'TOTAL')
    bh = EXP[cid]['byhand_total_before_tax']
    if cid == 'rf-move-eow':
        rep = 'match' if (pre == bh and shown['frequency'] == EXP[cid]['byhand_frequency_shown']) else 'differs'
    else:
        rep = 'match' if pre == bh else 'differs'
    rows.append(dict(id=cid, kind='price', status_as_reported='inconclusive', reason_as_reported='validator recorded total_before_tax = null (icon-font "$" broke its price pattern)',
                     reparsed_total_before_tax=pre, reparsed_total=tot, selections_shown=json.dumps(shown), selections_confirmed=sel_ok,
                     byhand_14oct=bh, reparsed_vs_byhand=rep, timestamp=r['timestamp'], screenshot=r['screenshot'],
                     screenshot_note='OVERWRITTEN by the next check (same file name)' if cid in ('rf-move-sq1000',) or (cid == 'rf-move-bd3' and False) else ''))
# screenshot collisions: find duplicate names
names = [r['screenshot'] for r in rf]
dups = {n for n in names if names.count(n) > 1}
for row in rows:
    if row['screenshot'] in dups and row['id'] != [x['id'] for x in rows if x['screenshot'] == row['screenshot']][-1]:
        row['screenshot_note'] = 'OVERWRITTEN by a later check with the same file name'
    elif row['screenshot'] in dups:
        row['screenshot_note'] = 'file shared with an earlier check (this is the surviving image)'
# Maid 2 Clean discovery observations
for n in R['notes']:
    if 'discovery host' in n: rows.append(dict(id='m2-disc-oldhost', kind='discovery', status_as_reported='observation', reason_as_reported=n))
    if 'booking page iframe' in n: rows.append(dict(id='m2-disc-iframe', kind='discovery', status_as_reported='observation', reason_as_reported=n))
for r in R['results']:
    if r['test'] == 'home-page price widget':
        f = 'one' if r['inputs']['frequency'].startswith('1 time') else 'biweekly'
        rows.append(dict(id=f"m2-widget-{r['inputs']['bedrooms']}-{r['inputs']['bathrooms']}-{f}", kind='discovery', status_as_reported='observation',
                         reason_as_reported=f"widget shows ${r['observed']['shown_per_clean']}/clean (not a booking-form price)", timestamp=r['timestamp'], screenshot=r['screenshot']))
# Launch27
done = {}
for r in R['results']:
    if r['test'].split(':')[0] in ('small', 'typical', 'larger'):
        key = 'super' if r['company'].startswith('Super') else 'm2'
        h, lab = r['test'].split(': ')
        c = {'one-time standard': 'one', 'biweekly standard': 'biweekly', 'one-time deep': 'deep'}[lab]
        done[f'l27-{key}-{h}-{c}'] = r
for key, err in [('super', 'ERROR in Launch27 Super Cleaning'), ('m2', 'ERROR in Launch27 Maid 2 Clean')]:
    first_missing = True
    for h in ['small', 'typical', 'larger']:
        for c in ['one', 'biweekly', 'deep']:
            cid = f'l27-{key}-{h}-{c}'
            if cid in done:
                r = done[cid]
                bh = EXP[cid]['byhand_pretax_first_visit']
                rows.append(dict(id=cid, kind='price', status_as_reported='passed' if r['match'] == 'yes' else r['match'],
                                 reason_as_reported=f"observed {r['observed']['pretax_first_visit']} = feed calc {r['calculated']}", byhand_14oct=bh,
                                 reparsed_vs_byhand='match' if r['observed']['pretax_first_visit'] == bh else 'differs', timestamp=r['timestamp'], screenshot=r['screenshot']))
            elif first_missing:
                first_missing = False
                rows.append(dict(id=cid, kind='price', status_as_reported='error', reason_as_reported='locator.evaluate: Timeout 30000ms exceeded - first check after the service change; the marked <select> was removed when Launch27 re-rendered the form'))
            else:
                rows.append(dict(id=cid, kind='price', status_as_reported='not_run', reason_as_reported='section stopped at the previous error'))

cols = ['id', 'kind', 'status_as_reported', 'reason_as_reported', 'reparsed_total_before_tax', 'reparsed_total', 'selections_confirmed', 'selections_shown', 'byhand_14oct', 'reparsed_vs_byhand', 'timestamp', 'screenshot', 'screenshot_note']
with open(HERE / 'check_status.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
price = [r for r in rows if r['kind'] == 'price']
cnt = lambda st: sum(1 for r in price if r['status_as_reported'] == st)
summary = dict(run='2026-10-15-13-48-53', note='derived after the run; original files in ./original are unchanged',
               price_checks=dict(planned=len(price), completed=cnt('passed') + cnt('inconclusive') + sum(1 for r in price if str(r['status_as_reported']).startswith('NO')),
                                 passed=cnt('passed'), failed=sum(1 for r in price if str(r['status_as_reported']).startswith('NO')), inconclusive=cnt('inconclusive'),
                                 error=cnt('error'), not_run=cnt('not_run')),
               red_feather_reparsed=dict(prices_recovered=sum(1 for r in price if r.get('reparsed_total_before_tax') is not None), match_byhand=sum(1 for r in price if r['id'].startswith('rf') and r.get('reparsed_vs_byhand') == 'match'),
                                         selections_confirmed=sum(1 for r in price if r['id'].startswith('rf') and r.get('selections_confirmed'))),
               discovery_observations=sum(1 for r in rows if r['kind'] == 'discovery'),
               checks=[dict(id=r['id'], kind=r['kind'], status=('passed' if r['status_as_reported'] == 'passed' else 'observation' if r['kind'] == 'discovery' else r['status_as_reported']), reason=r['reason_as_reported']) for r in rows])
json.dump(summary, open(HERE / 'summary.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != 'checks'}, indent=1))
print([r['id'] + ':' + r['screenshot_note'] for r in rows if r.get('screenshot_note')])
