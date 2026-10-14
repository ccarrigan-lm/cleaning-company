"""Normalize every captured price row into one auditable table.

Input : output/harvest/*/<capture>.csv (unchanged), Launch27 raw feeds (staged JSON),
        BookingKoala form metadata (*_form.csv).
Output: data/observations_normalized.csv.gz  every raw row, normalized, with include flag + reason
        data/analytical_prices.csv.gz        included rows, duplicates collapsed
        data/companies.csv                company registry (identity, city evidence, tiers, status)

Rules are listed in RULES below and referenced by id in `exclusion_reason` / `notes`.
Missing prices stay missing (never 0). Nothing is recomputed from assumptions except where a
rule says so (e.g. MIA tax-inclusive total / 1.06, validated against the 13 Oct live captures).
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd
from load_raw import load_bk_l27, load_forms, load_feeds, load_runlog, money

OUT = Path(__file__).resolve().parents[1] / 'data'
OUT.mkdir(exist_ok=True)

RULES = {
    'R1': 'Company-level exclusion (see companies.csv: template/demo form, wrong city, or capture failure)',
    'R2': 'BookingKoala row not verified: Booking Summary did not show the selected options (usually a service/frequency pair the form does not offer)',
    'R3': 'No usable price (blank or $0 displayed) - kept as missing, never treated as $0',
    'R4': 'Out of scope service (Airbnb/short-term rental, post-construction, commercial, carpet, hourly, single-room, non-cleaning)',
    'R5': 'Service prices identical to another service for every combination - likely the service switch did not register; needs live check',
    'R6': 'Launch27 row expanded a non-size counter (kitchen, laundry, stories...) above its minimum, or a per-sq-ft counter the harvester truncated',
    'R7': 'Placeholder/invalid option value (e.g. "Bedrooms", "None", malformed sq ft label)',
    'R8': 'Duplicate of another row with identical price and scope (non-pricing field differs only) - collapsed in analytical table',
    'R9': 'Zero-bathroom or zero-bedroom-not-studio combination (unrealistic home)',
    'R10': 'Duplicate service entry ("-Copy") on the form',
}

# ----------------------------------------------------------------------------- company registry
# city_evidence: what in the captured material ties the company to the assigned city.
#   title/domain = page title or domain names the city; search_only = only that the city search returned it;
#   contradicts = captured material points elsewhere.
REG = {
 'scrub-lou':              ('Scrub Lou', 'scrublou.com', 'louisville', 'title+13 Oct manual review (serves 40217)', ''),
 'maids-in-apron':         ('Maids in Apron', 'maidsinapron.com', 'louisville', '13 Oct manual review (serves 40217)', ''),
 'super-cleaning-louisville': ('Super Cleaning Service Louisville', 'supercleaningservicelouisville.com', 'louisville', 'domain + 13 Oct manual review', ''),
 'redfeathercleaning':     ('Red Feather Cleaning', 'redfeathercleaning.com', 'louisville', 'title ("Cleaning Services Louisville KY") + ZIP 40217 tax lookup returned 6%', ''),
 'deluxemaid':             ('Deluxe Maid', 'deluxemaid.com', 'indianapolis', 'search_only', 'R1: feed prices identical to bettercleans.com (Milwaukee) - looks like an unedited Launch27 template'),
 'indycleans':             ('Indy Cleans', 'indycleans.com', 'indianapolis', 'title', ''),
 'indycleaningpros':       ('Indy Cleaning Pros', 'indycleaningpros.com', 'indianapolis', 'title + domain', ''),
 'housekeepingmaideasy':   ('Housekeeping Maid Easy', 'housekeepingmaideasy.com', 'indianapolis', 'search_only', ''),
 'cleanmytribe':           ('CleanMyTribe', 'cleanmytribe.com', 'indianapolis', 'search_only', ''),
 'snmcleaningservices':    ('SNM Cleaning', 'snmcleaningservices.com', 'columbus', 'search_only', ''),
 'freshspacecleaning':     ('Fresh Space Cleaning', 'freshspacecleaning.com', 'columbus', 'contradicts: booking host is freshspacecleveland.launch27.com and the site was also returned for Memphis', 'R1: probably Cleveland, not Columbus; one-time frequency carries a 10% "discount" the harvester applied'),
 'brightstonecleaning':    ('Brightstone Cleaning', 'brightstonecleaning.com', 'columbus', 'title ("Hilliard & Columbus, OH"); 8% surcharge consistent with Ohio sales tax (unconfirmed)', ''),
 'lemonmaidcleaning':      ('Lemon Maid Cleaning', 'lemonmaidcleaning.com', 'columbus', 'title; ~5.75% surcharge consistent with Ohio state sales tax (unconfirmed)', ''),
 'maidcleaningnashville':  ('Maid Cleaning Nashville', 'maidcleaningnashville.com', 'nashville', 'title + domain', 'Every service is sold as a deep cleaning (frequency names say "Deep Cleaning")'),
 'wecleannashville':       ('We Clean Nashville', 'wecleannashville.com', 'nashville', 'title + domain', ''),
 'maidcomplete':           ('Maid Complete', 'maidcomplete.com', 'nashville', 'search_only', '4+ bedroom homes priced $0.09/sq ft; harvester truncated that counter (R6)'),
 'topknoxcleaning':        ('Top Knox Cleaning', 'topknoxcleaning.com', 'knoxville', 'domain', ''),
 'memphis-maids':          ('Memphis Maids', 'memphis-maids.com', 'memphis', 'title + domain', ''),
 'novohomeskc':            ('Novo Home Services', 'novohomeskc.com', 'kansas-city', 'domain ("kc")', ''),
 'bestcleankc':            ('Best Clean KC', 'bestcleankc.com', 'kansas-city', 'title ("Overland Park & Leawood", KS side of metro) + domain', ''),
 'divinemaids':            ('Divine Maids', 'divinemaids.com', 'oklahoma-city', 'search_only', 'Apartments priced by bedroom; houses priced by sq ft band only'),
 'spruceupcleaningco':     ('Spruce Up Cleaning Co', 'spruceupcleaningco.com', 'tulsa', 'title', ''),
 'adalynscleaning':        ("Adalyn's Cleaning", 'adalynscleaning.com', 'omaha', 'title', ''),
 'neatcorner':             ('Neat Corner', 'neatcorner.com', 'omaha', 'search_only', ''),
 'bearbroscleaning':       ('Bear Bros Cleaning', 'bearbroscleaning.com', 'birmingham', 'title lists Huntsville, Birmingham and 30A (multi-market; which market the prices apply to is unknown)', 'Capture stopped at the 60,000-row cap: standard ("Recurring Clean") service never captured'),
 'hercleaningcollective':  ('Her Cleaning Collective', 'hercleaningcollective.com', 'birmingham', 'search_only', ''),
 'consideritcleanrva':     ('Consider It Clean RVA', 'consideritcleanrva.com', 'richmond', 'title + domain ("rva")', ''),
 'kindlycleaners':         ('Kindly Cleaners', 'kindlycleaners.com', 'richmond', 'search_only', 'R1: form is a BookingKoala demo list (accountant, barber, dog walker...) with no prices'),
 'briocleaning':           ('Brio Cleaning', 'briocleaning.net', 'richmond', 'title', 'Bathrooms captured from a combined "full / half" select'),
 'bettercleans':           ('Better Cleans', 'bettercleans.com', 'milwaukee', 'search_only', 'R1: feed prices identical to deluxemaid.com (Indianapolis) - looks like an unedited Launch27 template'),
 'rapidscleaningservices': ('Rapids Cleaning Services', 'rapidscleaningservices.com', 'grand-rapids', 'title', 'No one-time frequency offered; deep/move never verified'),
}
EXCLUDE_COMPANY = {k for k, v in REG.items() if v[4].startswith('R1')}

# ----------------------------------------------------------------------------- parsers
WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'studio': 0}


def parse_beds(s):
    s = str(s).strip()
    if s == '':
        return np.nan, ''
    if re.fullmatch(r'(?i)bedrooms?|none|select.*', s):
        return np.nan, 'R7'
    if re.search(r'(?i)studio', s):
        return 0.0, ''
    m = re.search(r'\d+(\.\d+)?', s)
    return (float(m.group(0)), '') if m else (np.nan, 'R7')


def parse_baths(s):
    s = str(s).strip()
    if s == '':
        return np.nan, ''
    if re.fullmatch(r'(?i)bathrooms?|none|select.*', s):
        return np.nan, 'R7'
    m = re.match(r'(?i)\s*(\d+)\s*full\s*&\s*(\d+)\s*half', s)
    if m:
        return float(m.group(1)) + 0.5 * float(m.group(2)), ''
    m = re.search(r'\d+(\.\d+)?', s)
    return (float(m.group(0)), '') if m else (np.nan, 'R7')


def parse_sqft(label):
    """'1000 - 1499 Sq Ft' -> (1000,1499); 'Under 1,000' -> (0,999); '3,000+' -> (3000, inf)."""
    s = str(label).replace(',', '')
    s = re.sub(r'(?i)^(routine|deep|move-in/out|move in/out)\s*/\s*', '', s)
    if s.strip() == '' or s.strip().lower() == 'none':
        return np.nan, np.nan, ''
    n = [int(x) for x in re.findall(r'\d+', s)]
    if not n:
        return np.nan, np.nan, 'R7'
    if re.search(r'(?i)under|less|below', s):
        return 0, n[0] - 1 if n[0] % 10 == 0 else n[0], ''
    if len(n) == 1:
        if re.search(r'\+|over|-\s*$', s):
            return n[0], np.inf, ''
        return np.nan, np.nan, 'R7'   # e.g. bestcleankc "5"
    lo, hi = n[0], n[1]
    if hi < lo:
        return np.nan, np.nan, 'R7'
    return lo, hi, ''


def classify_service(name, addon='', company=''):
    s = f'{name} {addon}'.lower()
    if company == 'maidcleaningnashville':
        return 'move_in_out' if 'move' in addon.lower() else 'deep'
    if re.search(r'airbnb|vrbo|short term|vacation|hotel|post.?construct|construction|renovat|commercial|office|carpet|upholster|tile|grout|hourly|window|walkthrough|bathroom deep|accountant|barber|car wash|chiro|dog|tutor|esthet|financial|gutter|hair|lawn|lawyer|massage|moving service|nail|trainer|groom|photo|pool|spa\b|customize', s):
        return 'out_of_scope'
    if re.search(r'move', s):
        return 'move_in_out'
    if re.search(r'deep|initial|spring', s):
        return 'deep'
    return 'standard'


def norm_freq(f):
    s = (f or '').lower()
    if s in ('', '(none)'):
        return 'one_time'
    if re.search(r'one.?time|once|single|^o$', s) and 'quarter' not in s:
        return 'one_time'
    if re.search(r'2 ?weeks|other week|bi.?weekly|every two', s):
        return 'biweekly'
    if re.search(r'3 ?weeks|three ?weeks|semi monthly', s):
        return 'every_3_weeks'
    if re.search(r'4 ?weeks|monthly|month', s) and not re.search(r'bimonth|2 months|semiann', s):
        return 'every_4_weeks'
    if re.search(r'twice a week|daily', s):
        return 'other'
    if re.search(r'week', s) and not re.search(r'6|8|12|24', s):
        return 'weekly'
    return 'other'   # every 6/8 weeks, quarterly, semiannual...


# ----------------------------------------------------------------------------- BookingKoala
def normalize_bk(raw, forms):
    d = raw[raw.schema == 'bookingkoala'].copy()
    out = pd.DataFrame({
        'company_id': d.company_id, 'source_file': d.source_file, 'source_row': d.source_row,
        'platform': 'BookingKoala', 'captured': d.captured, 'site_service': d.service,
        'frequency_raw': d.frequency, 'bedrooms_raw': d.bedrooms, 'bathrooms_raw': d.bathrooms,
        'sqft_label': d.sqft, 'other_options': d.otherOptions,
    })
    tbt, tot, rec = d.totalBeforeTax.map(money), d.total.map(money), d.recurringTotal.map(money)
    tax = d.taxRatePct.map(money)
    out['displayed_total_before_tax'] = tbt
    out['displayed_total'] = tot
    out['displayed_recurring_total'] = rec
    out['zip_used'] = [d_zip if (forms.get(c, {}).get('zipFound') == 'true') else '' for c, d_zip in zip(d.company_id, d.zip)]
    out['zip_entered'] = [forms.get(c, {}).get('zipFound') == 'true' for c in d.company_id]
    out['surcharge_pct_over_pretax'] = ((tot / tbt - 1) * 100).round(2)
    # Pre-tax first-visit / per-visit price
    pre, basis = [], []
    for c, a, b, t in zip(d.company_id, tbt, tot, tax):
        if a is not None and not np.isnan(a):
            pre.append(a); basis.append('total before tax/fees as displayed')
        elif b is not None and not np.isnan(b) and t == 6 and c == 'maids-in-apron':
            pre.append(round(b / 1.06, 2)); basis.append('displayed total / 1.06 (MIA total includes 6% KY tax; matches 13 Oct live checks)')
        elif b is not None and not np.isnan(b):
            pre.append(b); basis.append('displayed total; site shows one total and whether it includes tax is unknown')
        else:
            pre.append(np.nan); basis.append('no price displayed')
    out['price_first_or_per_visit'] = pre
    out['price_basis'] = basis
    # Ongoing recurring visit
    r_pre = []
    for c, r in zip(d.company_id, rec):
        if r is None or np.isnan(r):
            r_pre.append(np.nan)
        else:
            r_pre.append(round(r / 1.06, 2) if c == 'maids-in-apron' else r)
    out['price_ongoing_visit'] = r_pre
    out['verified_live'] = d.verified.eq('true')
    out['evidence_tier'] = 'live form observation'
    return out


# ----------------------------------------------------------------------------- Launch27
def bed_from_service(name):
    s = name.lower()
    m = re.search(r'(\d+)\s*\+?\s*bed', s)
    if m:
        return float(m.group(1)), ('+' in s[m.start():m.end() + 1])
    for w, n in WORDNUM.items():
        if re.search(rf'\b{w}\b.*bed|^{w}\b', s):
            return float(n), False
    return np.nan, False


def sqft_from_service(name):
    s = name.replace(',', '')
    m = re.search(r'(\d+)\s*-\s*(\d+)\s*(square|sq)', s, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'under\s*-?\s*(\d+)', s, re.I)
    if m:
        return 0, int(m.group(1))
    m = re.search(r'(\d+)\s*\+\s*(square|sq)', s, re.I)
    if m:
        return int(m.group(1)), np.inf
    return np.nan, np.nan


SIZE_PARAM = re.compile(r'bed|bath|sq|feet|footage|size', re.I)


def normalize_l27(raw, feeds):
    d = raw[raw.schema == 'launch27'].copy()
    rows = []
    for _, r in d.iterrows():
        cid = r.company_id
        feed = feeds.get(cid, {})
        svc = next((s for s in feed.get('services', {}).get('services', []) if s['name'] == r.service), None)
        mins = {p['name']: (p.get('quantity_minimum'), p['type'], (p.get('ranges') or [{}])[0].get('label')) for p in (svc or {}).get('pricing_parameters') or []}
        opts = dict(kv.split('=', 1) for kv in r.options.split('; ') if '=' in kv)
        bad_counter = False
        for name, val in opts.items():
            if name not in mins:
                continue
            mn, typ, first_label = mins[name]
            if not SIZE_PARAM.search(name) or re.search(r'trip', name, re.I):
                if typ == 'flat' and str(val) != str(mn):
                    bad_counter = True
                if typ == 'ranged' and val != first_label:
                    bad_counter = True
        # per-sq-ft flat counters (e.g. maidcomplete "Square Footage" $0.09 x 1500..9000) were truncated by the harvester
        per_sqft = any(p['type'] == 'flat' and SIZE_PARAM.search(p['name']) and re.search(r'sq|feet|footage', p['name'], re.I) and 0 < float(p.get('price') or 0) < 1
                       for p in (svc or {}).get('pricing_parameters') or [])
        beds, plus = bed_from_service(r.service)
        if np.isnan(beds) and r.bedrooms:
            beds = float(r.bedrooms)
        lo, hi = sqft_from_service(r.service)
        if np.isnan(lo) and r.sqft and not per_sqft:
            lo, hi, _ = parse_sqft(r.sqft)
        fb = float(r.fullBaths) if r.fullBaths != '' else np.nan
        hb = float(r.halfBaths) if r.halfBaths != '' else np.nan
        baths = float(r.bathrooms) if r.bathrooms != '' else np.nan
        # bedroom / bathroom counters priced $0 (housekeepingmaideasy) do not change the price -> treat as "any"
        zero_priced = {p['name'] for p in (svc or {}).get('pricing_parameters') or [] if p['type'] == 'flat' and float(p.get('price') or 0) == 0}
        if any(re.search(r'bed', n, re.I) for n in zero_priced):
            beds = np.nan
        if any(re.search(r'bath', n, re.I) for n in zero_priced):
            baths = fb = hb = np.nan
        rows.append(dict(company_id=cid, source_file=r.source_file, source_row=r.source_row, platform='Launch27', captured=r.captured,
                         site_service=r.service + (f' + {r.addOn}' if r.addOn else ''), addon=r.addOn, frequency_raw=r.frequency,
                         bedrooms=beds, bedrooms_plus=plus, bathrooms=baths, full_baths=fb, half_baths=hb, sqft_label=r.sqft or '',
                         sqft_min=lo, sqft_max=hi, other_options=r.options,
                         price_first_or_per_visit=money(r.firstVisitPreTax), price_ongoing_visit=money(r.recurringVisitPreTax),
                         price_basis="calculated from the site's Launch27 price feed (base + parameters, frequency % per feed rules); tax not included",
                         verified_live=np.nan, evidence_tier='booking-platform feed calculation',
                         r6=bad_counter or (per_sqft and bool(r.sqft)), zip_used='', zip_entered=False))
    out = pd.DataFrame(rows)
    out.loc[out.company_id == 'super-cleaning-louisville', 'evidence_tier'] = 'booking-platform feed calculation (3 live spot checks 13 Oct matched)'
    return out


# ----------------------------------------------------------------------------- main
def main():
    raw = load_bk_l27()
    forms, feeds = load_forms(), load_feeds()
    bk = normalize_bk(raw, forms)
    # parse BK sizes
    b = bk.bedrooms_raw.map(parse_beds); bk['bedrooms'] = [x[0] for x in b]; bk['r7_bed'] = [x[1] for x in b]
    ba = bk.bathrooms_raw.map(parse_baths); bk['bathrooms'] = [x[0] for x in ba]; bk['r7_bath'] = [x[1] for x in ba]
    # Brio: bathrooms live in a combined select captured as other_options
    m = bk.company_id.eq('briocleaning') & bk.other_options.str.startswith('Bathrooms (full / half)=')
    bk.loc[m, 'bathrooms'] = bk.loc[m, 'other_options'].str.split('=').str[1].map(lambda s: parse_baths(s)[0])
    bk.loc[m, 'bathrooms_raw'] = bk.loc[m, 'other_options'].str.split('=').str[1]
    bk.loc[m, 'other_options'] = ''
    sq = bk.sqft_label.map(parse_sqft)
    bk['sqft_min'] = [x[0] for x in sq]; bk['sqft_max'] = [x[1] for x in sq]; bk['r7_sq'] = [x[2] for x in sq]
    bk['addon'] = ''
    bk['full_baths'] = np.nan; bk['half_baths'] = np.nan; bk['bedrooms_plus'] = False
    l27 = normalize_l27(raw, feeds)
    df = pd.concat([bk, l27], ignore_index=True, sort=False)
    df['service'] = [classify_service(s, a, c) for s, a, c in zip(df.site_service, df.addon.fillna(''), df.company_id)]
    df['frequency'] = df.frequency_raw.map(norm_freq)
    df['company'] = df.company_id.map(lambda c: REG[c][0])
    df['city'] = df.company_id.map(lambda c: REG[c][2])

    # ---- inclusion rules (first matching reason wins; all reasons kept in `flags`)
    flags = [[] for _ in range(len(df))]
    def flag(mask, rule):
        for i in np.flatnonzero(mask.to_numpy()):
            flags[i].append(rule)
    flag(df.company_id.isin(EXCLUDE_COMPANY), 'R1')
    flag(df.platform.eq('BookingKoala') & ~df.verified_live.fillna(False).astype(bool), 'R2')
    flag(df.price_first_or_per_visit.isna() | df.price_first_or_per_visit.eq(0), 'R3')
    flag(df.service.eq('out_of_scope'), 'R4')
    flag(df.company_id.eq('redfeathercleaning') & df.site_service.isin(['Move In/Out Clean', 'Construction Clean Up']), 'R5')
    flag(df.get('r6', pd.Series(False, index=df.index)).fillna(False).astype(bool), 'R6')
    flag((df.get('r7_bed', '').fillna('') != '') | (df.get('r7_bath', '').fillna('') != '') | (df.get('r7_sq', '').fillna('') != ''), 'R7')
    flag((df.bathrooms.eq(0)) | (df.full_baths.eq(0) & df.half_baths.fillna(0).eq(0)), 'R9')
    flag(df.site_service.str.contains('-Copy', na=False) | df.sqft_label.str.contains('-Copy', na=False), 'R10')
    df['flags'] = [';'.join(f) for f in flags]
    df['include'] = df['flags'].eq('')
    df['exclusion_reason'] = [RULES[f[0]] if f else '' for f in flags]

    # ---- recurring basis
    def rbasis(r):
        if r.frequency == 'one_time':
            return 'n/a (one-time)'
        if r.platform == 'Launch27':
            return 'calculated: feed discount ' + ('applies from the 2nd visit (first visit full price)' if r.price_first_or_per_visit != r.price_ongoing_visit else 'applies to every visit incl. first')
        if not np.isnan(r.price_ongoing_visit):
            return 'displayed separately as recurring total'
        return 'single per-visit total shown for this frequency; site does not say whether the first visit differs'
    df['recurring_basis'] = df.apply(rbasis, axis=1)

    # ---- dedupe key: everything that defines price + scope
    key = ['company_id', 'service', 'site_service', 'frequency', 'frequency_raw', 'bedrooms', 'bathrooms', 'full_baths', 'half_baths',
           'sqft_min', 'sqft_max', 'price_first_or_per_visit', 'price_ongoing_visit']
    k = df[key[0]].map(str)
    for c in key[1:]:
        k = k + '|' + df[c].map(str)
    df['dedupe_group'] = pd.factorize(k)[0]
    inc = df[df.include]
    dup_first = ~inc.duplicated('dedupe_group', keep='first')
    df['is_duplicate_of_earlier_row'] = False
    df.loc[inc.index[~dup_first.to_numpy()], 'is_duplicate_of_earlier_row'] = True
    df.loc[df.is_duplicate_of_earlier_row, 'flags'] = 'R8'

    cols = ['company_id', 'company', 'city', 'platform', 'evidence_tier', 'captured', 'service', 'site_service', 'frequency', 'frequency_raw',
            'bedrooms', 'bathrooms', 'full_baths', 'half_baths', 'bedrooms_raw', 'bathrooms_raw', 'sqft_label', 'sqft_min', 'sqft_max', 'other_options',
            'price_first_or_per_visit', 'price_ongoing_visit', 'price_basis', 'recurring_basis', 'displayed_total_before_tax', 'displayed_total',
            'displayed_recurring_total', 'surcharge_pct_over_pretax', 'zip_used', 'zip_entered', 'verified_live', 'include', 'flags', 'exclusion_reason',
            'is_duplicate_of_earlier_row', 'dedupe_group', 'source_file', 'source_row']
    df = df.reindex(columns=cols)
    df.to_csv(OUT / 'observations_normalized.csv.gz', index=False, compression='gzip')
    ana = df[df.include & ~df.is_duplicate_of_earlier_row].drop(columns=['include', 'is_duplicate_of_earlier_row', 'exclusion_reason'])
    ana.to_csv(OUT / 'analytical_prices.csv.gz', index=False, compression='gzip')
    df.to_pickle(Path(__file__).with_name('.norm_cache.pkl'))
    print(f'normalized {len(df):,} rows; included {df.include.sum():,}; analytical (deduped) {len(ana):,}')
    return df


if __name__ == '__main__':
    main()
