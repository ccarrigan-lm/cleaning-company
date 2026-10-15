"""Run 2 (2026-10-15-14-08-17, --rerun of run 1) + combined status across runs 1 and 2. Original files in ./original are untouched."""
import collections, json, re
from pathlib import Path
HERE = Path(__file__).parent
S2 = json.load(open(HERE / 'original' / 'summary.json'))
N2 = json.load(open(HERE / 'original' / 'network_requests.json'))
S1 = json.load(open(HERE.parent / '2026-10-15-automated-run1' / 'summary.json'))
CAT = [(r'^https://r\.stripe\.com/b$', 'third-party: Stripe.js telemetry'), (r'^https://m\.stripe\.com/6$', 'third-party: Stripe fraud fingerprint'),
       (r'^https://merchant-ui-api\.stripe\.com/elements/wallet-config$', 'third-party: Stripe wallet config'),
       (r'^https://api\.hcaptcha\.com/(checksiteconfig|getcaptcha/[\w-]+)$', 'third-party: hCaptcha load/challenge'),
       (r'^https://(analytics\.google\.com|stats\.g\.doubleclick\.net)/g/collect$', 'third-party: Google Analytics/DoubleClick'),
       (r'^https://sessions\.bugsnag\.com/$', 'third-party: Bugsnag'), (r'(driftapi|drift)\.com/', 'third-party: Drift chat'),
       (r'launch27\.com/v1/booking/estimate_price$', 'first-party: Launch27 price estimate'), (r'launch27\.com/v1/booking/spots$', 'first-party: Launch27 time slots'),
       (r'bookingkoala\.com/(cdn-cgi/rum|api/v4/form-custom-fields|api/v7/addons/search|leads/v1/pages/popups)$', 'first-party: BookingKoala page-load config/beacon')]
first = [x for x in N2 if re.search(r'bookingkoala|supercleaning\.launch27|smilesaremaid', x['url'])]
def page_of(x):
    prev = [f for f in first if f['ts'] <= x['ts']]
    return prev[-1]['url'].split('/')[2] if prev else (x.get('frameUrl') or '').split('/')[2] if x.get('frameUrl') else '?'
rows = collections.Counter()
for x in N2:
    cat = next((c for p, c in CAT if re.search(p, x['url'])), 'UNEXPECTED')
    rows[(cat, page_of(x))] += 1
net = {'total': len(N2), 'blocked': sum(x['blocked'] for x in N2), 'by_category_and_page': [dict(category=c, page=p, count=n) for (c, p), n in sorted(rows.items())],
       'unexpected_after_review': sum(n for (c, p), n in rows.items() if c == 'UNEXPECTED'),
       'first_party_hosts_posted_to': sorted({x['url'].split('/')[2] for x in N2 if re.search(r'launch27|bookingkoala', x['url'])}),
       'max_post_bytes_third_party': max((x.get('postDataBytes') or 0) for x in N2 if not re.search(r'launch27|bookingkoala', x['url']))}
s1 = {c['id']: c for c in S1['checks']}; s2 = {c['id']: c for c in S2['checks']}
combined = []
for cid, c1 in s1.items():
    c2 = s2.get(cid)
    if c1['status'] == 'passed': final, src = 'passed', 'run 1'
    elif c2 and c2['status'] not in ('not_run',): final, src = c2['status'], 'run 2'
    else: final, src = c1['status'], 'run 1'
    combined.append(dict(id=cid, kind=c1['kind'], run1=c1['status'], run2=(c2 or {}).get('status', 'not in run 2'), final=final, final_from=src))
price = [c for c in combined if c['kind'] == 'price']
out = dict(runs=['2026-10-15-13-48-53', '2026-10-15-14-08-17'], price_checks_planned=len(price),
           final=dict(collections.Counter(c['final'] for c in price)), discovery_observations=dict(run1=sum(c['kind'] == 'discovery' for c in combined), run2='not selected'),
           red_feather_structure_run2=[n for n in S2['notes'] if n.startswith('Red Feather')], network_run2=net, checks=combined)
json.dump(out, open(HERE / 'combined_status.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('checks',)}, indent=1)[:4000])
