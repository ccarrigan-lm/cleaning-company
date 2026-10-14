"""Registry, availability categories, extras, scope, coverage and issue log."""
import csv, json, re
from pathlib import Path
import numpy as np
import pandas as pd
from load_raw import load_feeds, load_runlog
from normalize import REG, EXCLUDE_COMPANY

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / 'data'
ROOT = HERE.parents[2]
norm = pd.read_pickle(Path(__file__).with_name('.norm_cache.pkl'))
ana = pd.read_csv(DATA / 'analytical_prices.csv.gz', low_memory=False)
prof = pd.read_csv(DATA / 'profile_prices_all.csv', low_memory=False)
struct = pd.read_csv(DATA / 'structure_by_company.csv')
run = load_runlog()
CITIES = {c['id']: c for c in json.load(open(ROOT / 'config' / 'cities.json'))['cities']}

# ----------------------------------------------------------------------------- companies
rows = []
for cid, (name, domain, city, ev, note) in REG.items():
    rl = run[run.companyId == cid]
    n = norm[norm.company_id == cid]
    a = ana[ana.company_id == cid]
    tier = n.evidence_tier.iloc[0] if len(n) else ''
    if cid in EXCLUDE_COMPANY:
        status = 'excluded (' + note.split(':', 1)[1].strip() + ')'
    elif cid == 'bearbroscleaning':
        status = 'partial (row cap hit; standard service missing)'
    elif cid == 'rapidscleaningservices':
        status = 'partial (standard recurring only; deep/move unverified)'
    else:
        status = 'usable'
    rows.append(dict(company_id=cid, company=name, domain=domain, assigned_city=CITIES[city]['name'], state=CITIES[city]['state'],
                     city_evidence=ev, service_area_confirmed='yes (13 Oct manual review)' if '13 Oct' in ev else 'no',
                     platform=rl.platform.iloc[0] if len(rl) else '', evidence_tier=tier, capture_status=status,
                     zip_entered=bool(n.zip_entered.any()) if len(n) else False, zip_used=(n.zip_used[n.zip_used.astype(str) != ''].astype(str).iloc[0] if len(n) and (n.zip_used.astype(str) != '').any() else ''),
                     raw_rows=len(n), raw_unverified=int((n.platform.eq('BookingKoala') & ~n.verified_live.fillna(False).astype(bool)).sum()),
                     included_rows=int(n.include.sum()), analytical_rows_after_dedupe=len(a),
                     services_in_analysis=', '.join(sorted(a.service.unique())), notes=note,
                     run_seconds=rl.seconds.iloc[0] if len(rl) else '', source_file=n.source_file.iloc[0] if len(n) else ''))
# capture failures and 13 Oct manual sources
for cid, name, city, plat, why in [
        ('patriotmaids', 'Patriot Maids', 'cincinnati', 'BookingKoala', 'Browser closed after 52 min (0 rows saved); multi-city franchise - city assignment uncertain'),
        ('stlouiscleansolutions', 'St. Louis Clean Solutions', 'st-louis', 'BookingKoala', 'Ran 7.7 h without saving (0 rows)'),
        ('hometownclean', 'HomeTown Clean', 'cincinnati', 'BookingKoala', 'Wrong form URL (cdn.bookingkoala.com) - 1 junk row, removed from harvest folder 14 Oct'),
        ('thevalleycleanteam', 'The Valley Clean Team', 'nashville', 'BookingKoala', 'Title says North Alabama & Nashville; 3 unverified rows, removed 14 Oct'),
        ('maggymaid', 'Maggy Maid', 'nashville', 'Launch27', 'Only service is vacation rental/Airbnb; 80,000 junk rows moved to output/harvest/_excluded'),
        ('sprucedupcleans', 'Spruced Up Cleans', 'columbus', 'Launch27', 'Room-count pricing; harvester expanded non-size counters into 80,000 junk rows (moved to _excluded). Feed rules documented on Structure sheet.')]:
    rows.append(dict(company_id=cid, company=name, domain='', assigned_city=CITIES[city]['name'], state=CITIES[city]['state'], city_evidence='search_only',
                     service_area_confirmed='no', platform=plat, evidence_tier='', capture_status='not captured / excluded', notes=why, raw_rows=0,
                     included_rows=0, analytical_rows_after_dedupe=0))
rows.append(dict(company_id='maid2cleanky', company='Maid 2 Clean KY', domain='maid2cleanky.com', assigned_city='Louisville', state='KY',
                 city_evidence='site address 9850 Von Allmen Ct, Louisville (14 Oct)', service_area_confirmed='no', platform='Launch27',
                 evidence_tier='booking-platform feed calculation (Launch27 smilesaremaid.launch27.com, 14 Oct; 9 live checks matched)',
                 capture_status='14 Oct validation capture (modelled from feed)',
                 notes='14 Oct harvest found 0 rows: detected host maidtocleanky.launch27.com returns 403 "client is not active"; the booking page iframe uses smilesaremaid.launch27.com. Feed summary + 9 live form checks in research/validation/2026-10-14/maid2clean_live.json.',
                 raw_rows=0, included_rows=0, analytical_rows_after_dedupe=0, source_file='research/validation/2026-10-14/maid2clean_live.json'))
for name, tier, note in [
        ('Rocking Robins (R&R) Maids', 'reconstructed calculator formula (13 Oct; 1 combination checked live)', 'First clean only; recurring price must be quoted'),
        ('Cleanoria (Thumbtack)', 'published price range (13 Oct)', 'Ranges from the Thumbtack pricing FAQ; not quotes'),
        ('Stitch Cleaning', 'published price list (13 Oct)', 'Bed/bath flat list; no sq ft; half baths not priced'),
        ('Your Cleaning Krew', 'published price range (13 Oct)', 'Broad "$X-$Y+" ranges by bedroom group'),
        ('Busy Brooms', 'published price range (13 Oct)', 'Page may describe market ranges rather than own rates'),
        ('Hello Cleaners', 'published "from" price (13 Oct)', 'National operator; floor prices only'),
        ('LouBelle Cleaning', 'published hourly rate (13 Oct)', '$40/hr per technician, 2-technician minimum')]:
    rows.append(dict(company_id=re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'), company=name, assigned_city='Louisville', state='KY',
                     city_evidence='13 Oct manual review', service_area_confirmed='yes (13 Oct manual review)', platform='', evidence_tier=tier,
                     capture_status='13 Oct manual capture', notes=note))
companies = pd.DataFrame(rows)
companies.to_csv(DATA / 'companies.csv', index=False)

# ----------------------------------------------------------------------------- price availability (do NOT infer "hidden" from no detection)
disc = list(csv.DictReader(open(ROOT / 'output' / 'discovery' / '2026-10-14-00-24-59.csv', encoding='utf-8-sig')))
by_dom = {}
for r in disc:
    by_dom.setdefault(r['domain'], []).append(r)
captured_domains = {v[1] for k, v in REG.items() if k not in EXCLUDE_COMPANY}
av = []
for dom, rs in by_dom.items():
    r0 = max(rs, key=lambda r: int(r['pagesChecked'] or 0))
    plat = r0['platform']
    if dom == 'cleanestimator.com':
        cat, why = 'not a cleaning company', 'cost-calculator website'
    elif dom in captured_domains:
        cat, why = 'working instant calculator', 'captured and usable in this analysis' + (' (CORRECTION: 13 Oct workbook listed Red Feather as lead-form only)' if dom == 'redfeathercleaning.com' else '')
    elif r0['harvestable'] == 'true':
        cat, why = 'instant calculator detected - not usable yet', 'detected BookingKoala/Launch27 form; capture failed or excluded (see companies.csv)'
    elif plat in ('jobber', 'zenmaid', 'housecallpro', 'maidily'):
        cat, why = 'unknown / unreviewed', f'{plat} booking link detected; whether it shows prices before contact details was not reviewed'
    else:
        cat, why = 'unknown / unreviewed', ('only the home page loaded' if r0['pagesChecked'] in ('1', '0', '') else f"{r0['pagesChecked']} pages checked; no BookingKoala/Launch27 signature found") + \
            ' - this does NOT mean prices are hidden (published lists, other calculators and contact forms were not looked for)'
    av.append(dict(domain=dom, cities_returned_by_search=', '.join(sorted({x['city'] for x in rs})), page_title=r0['name'], category=cat,
                   detected_platform=plat, pages_checked=r0['pagesChecked'], basis=why, source='output/discovery/2026-10-14-00-24-59.csv'))
for name, cat, basis in [
        ('Stitch Cleaning', 'public price list', '13 Oct: stitchcleaning.com pricing page'), ('Your Cleaning Krew', 'public price list', '13 Oct: published ranges'),
        ('Busy Brooms', 'public price list', '13 Oct: published ranges (possibly market ranges)'), ('Hello Cleaners', 'public price list', '13 Oct: "from" prices'),
        ('Super Cleaning Service Louisville', 'public price list', '13 Oct: services page ranges (also has instant calculator)'),
        ('Rocking Robins (R&R) Maids', 'working instant calculator', '13 Oct: price shown before contact fields (also publishes ranges)'),
        ('LouBelle Cleaning', 'public price list', '13 Oct: published hourly rate; exact quote by phone'),
        ('Cleanoria (Thumbtack)', 'public price list', '13 Oct: Thumbtack pricing FAQ'),
        ('Maid in the Ville', 'contact-gated quote', '13 Oct: estimate form asks name, email, phone, address'),
        ('The Cleaning Authority - Louisville', 'contact-gated quote', '13 Oct: price shown after name/phone/email/address step'),
        ('MaidPro - Greater Louisville', 'contact-gated quote', '13 Oct: estimate request form'),
        ('Merry Maids - Louisville', 'contact-gated quote', '13 Oct: quote flow starts with street address'),
        ('The Maids - Louisville', 'contact-gated quote', '13 Oct: "Your Pricing" after contact info')]:
    av.append(dict(domain=name, cities_returned_by_search='louisville (13 Oct manual)', page_title='', category=cat, detected_platform='', pages_checked='',
                   basis=basis, source='research/2026-10-13/Louisville_Cleaning_Price_Matrix.xlsx (Round 1 Tracker, Published Prices)'))
avail = pd.DataFrame(av)
avail.to_csv(DATA / 'price_availability.csv', index=False)

# ----------------------------------------------------------------------------- extras
feeds = load_feeds()
ex = []
for cid, f in feeds.items():
    if cid not in REG or cid in EXCLUDE_COMPANY:
        continue
    for s in f['services']['services']:
        for e in s.get('extras', []):
            ex.append(dict(company=REG[cid][0], city=CITIES[REG[cid][2]]['name'], service=s['name'], extra=e['name'], price=float(e.get('price') or 0),
                           per_unit=bool(e.get('quantity_based')), evidence_tier='booking-platform feed', recurring_discount_applies='unknown',
                           source=f'output/harvest/{cid}/2026-10-14-00-52-02_raw-feed.json'))
x = pd.DataFrame(ex)
# collapse identical extras repeated on every bedroom service
x = x.groupby(['company', 'city', 'extra', 'price', 'per_unit', 'evidence_tier', 'recurring_discount_applies', 'source'], as_index=False).agg(services=('service', lambda s: f'{len(set(s))} services'))
x13 = [('Scrub Lou', 'Inside oven', 45, False), ('Scrub Lou', 'Inside fridge', 45, False), ('Scrub Lou', 'Interior windows, glass only (per window)', 4, True),
       ('Scrub Lou', 'Interior windows, glass & tracks (per window)', 8, True), ('Scrub Lou', 'Basement', np.nan, False),
       ('Scrub Lou', 'Exclude a bedroom / full bath / kitchen / living room (credit)', -10, True), ('Scrub Lou', 'Exclude a half bath (credit)', -5, True),
       ('Maids in Apron', 'Inside oven', 45, False), ('Maids in Apron', 'Inside fridge', 45, False), ('Maids in Apron', 'Interior windows (per window)', 5, True),
       ('Maids in Apron', 'Wet-wipe blinds (per unit)', 5, True), ('Maids in Apron', 'Inside cabinets (per unit)', 5, True), ('Maids in Apron', 'Finished basement', 120, False),
       ('Maids in Apron', 'Extra kitchen', 90, False), ('Maids in Apron', 'Pets', 10, False), ('Maids in Apron', 'Laundry & folding', 65, False),
       ('Maids in Apron', 'Dishes', 65, False), ('Maids in Apron', 'House organization', 375, False), ('Maids in Apron', 'Green cleaning', 0, False),
       ('Rocking Robins (R&R) Maids', 'Interior windows (each)', 5, True), ('Rocking Robins (R&R) Maids', 'Blinds (each)', 20, True),
       ('Rocking Robins (R&R) Maids', 'Fridge / freezer (each)', 60, True)]
for c, e, p_, u in x13:
    x = pd.concat([x, pd.DataFrame([dict(company=c, city='Louisville', extra=e, price=p_, per_unit=u, evidence_tier='live form observation (13 Oct manual)',
                                         recurring_discount_applies='yes (Scrub Lou: same % as base)' if c == 'Scrub Lou' else 'unknown',
                                         source='research/2026-10-13/*_model.json', services='')])], ignore_index=True)
x.loc[x.company.str.startswith('Super Cleaning'), 'recurring_discount_applies'] = 'yes, except Additional Time (13 Oct model)'
x.to_csv(DATA / 'extras.csv', index=False)

# ----------------------------------------------------------------------------- scope / included tasks (what was actually captured)
scope = [
 ('Scrub Lou', 'Routine / Deep / Move-In-Out', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'Room exclusions and extras listed (oven, fridge, interior windows, basement=custom quote); deep clean recommended (not required) before recurring; pets field', 'docs/scrub-lou-form-notes.md'),
 ('Maids in Apron', 'Flat-rate house cleaning; deep and move-in/out are add-ons', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', '12 extras incl. inside cabinets, blinds, laundry, dishes, organization', 'research/2026-10-13/maids_in_apron_model.json'),
 ('Super Cleaning Service Louisville', 'Bedroom-based home cleaning + deep / move add-ons', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'Extras incl. oven, fridge/freezer, windows, couch vacuuming, extra time', 'Round 1 Tracker (13 Oct); raw feed'),
 ('Red Feather Cleaning', 'Basic / Deep / Move In-Out / Commercial / Construction', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'None captured', 'output/harvest/redfeathercleaning/*'),
 ('Rocking Robins (R&R) Maids', '1st-time basic vs 1st-time deep; condition, stories, basement change hours', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'Windows, blinds, fridge/freezer', 'research/2026-10-13/rr_maids_model.json'),
 ('Stitch Cleaning', 'Standard (flat by bed/bath)', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'n/a', '13 Oct published list'),
 ('Cleanoria (Thumbtack)', 'Standard / Deep ranges', 'CAPTURED 14 Oct - see research/checklists/2026-10-14', 'Supplies included (FAQ)', 'research/2026-10-13/cleanoria_model.json'),
 ('MaidPro - Greater Louisville', 'n/a (contact-gated)', 'CAPTURED 14 Oct (49-point checklist) - see research/checklists/2026-10-14', 'n/a', 'Round 1 Tracker'),
 ('Bear Bros Cleaning (Birmingham)', 'Move-In/Out (47-Step), Deep (44-Step), Recurring (33-Step)', 'Step counts in service names only - checklist NOT captured', 'n/a', 'form service names'),
 ('Launch27 peers (several)', 'Add-on names describe scope', 'Partial: e.g. move-out "includes oven & fridge" (Indy Cleaning Pros, Maid Cleaning Nashville), "inside windows, cupboards and appliances" (CleanMyTribe), "unfurnished deep clean incl. fridge, oven, cabinets" (Top Knox)', 'see extras.csv', 'raw feeds'),
]
pd.DataFrame(scope, columns=['company', 'services_offered', 'included_tasks_checklist', 'extras_exclusions_captured', 'source']).to_csv(DATA / 'scope.csv', index=False)

# ----------------------------------------------------------------------------- city coverage
cov = []
for cid_city, c in CITIES.items():
    comp = companies[(companies.assigned_city == c['name'])]
    usable = comp[comp.capture_status.isin(['usable']) | comp.capture_status.str.startswith('partial') | comp.capture_status.eq('13 Oct manual capture')]
    a = ana[ana.city == cid_city]
    s = struct[struct.city == cid_city]
    std = s.std_one_time.dropna()
    cov.append(dict(city=c['name'], state=c['state'], search_zip=c['zip'], companies_found_with_instant_calculator=int((comp.platform != '').sum()),
                    usable_instant_calculator_companies=int(comp.capture_status.isin(['usable']).sum() + comp.capture_status.str.startswith('partial').sum()),
                    companies_with_standard_one_time_ref_price=len(std),
                    ref_home_std_one_time_min=std.min() if len(std) else np.nan, ref_home_std_one_time_median=std.median() if len(std) else np.nan,
                    ref_home_std_one_time_max=std.max() if len(std) else np.nan, analytical_rows=len(a),
                    note='Louisville also has 13 Oct models/published lists (see Louisville sheets)' if cid_city == 'louisville' else
                         ('no usable data' if len(a) == 0 else ('n<3: structure examples only' if len(std) < 3 else 'small, non-random sample'))))
pd.DataFrame(cov).to_csv(DATA / 'city_coverage.csv', index=False)
print(companies.capture_status.value_counts().to_string())
print(avail.category.value_counts().to_string())
print(pd.DataFrame(cov)[['city', 'usable_instant_calculator_companies', 'companies_with_standard_one_time_ref_price', 'ref_home_std_one_time_median']].to_string())

# ----------------------------------------------------------------------------- rule counts
from normalize import RULES
first = norm['flags'].fillna('').str.split(';').str[0]
rc = [dict(rule=k, rule_text=v, rows_first_reason=int((first == k).sum()), rows_flagged_any=int(norm['flags'].fillna('').str.split(';').map(lambda l: k in l).sum()))
      for k, v in RULES.items()]
rc.append(dict(rule='-', rule_text='Included in analytical table after de-duplication', rows_first_reason=int((norm.include & ~norm.is_duplicate_of_earlier_row).sum()), rows_flagged_any=None))
rc.append(dict(rule='-', rule_text='Total raw rows', rows_first_reason=len(norm), rows_flagged_any=None))
pd.DataFrame(rc).to_csv(DATA / 'rule_counts.csv', index=False)
print(pd.DataFrame(rc)[['rule', 'rows_first_reason', 'rows_flagged_any']].to_string())
