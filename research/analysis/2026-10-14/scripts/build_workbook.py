"""Write Louisville_Comparison_Validated.xlsx from the audited CSVs."""
from pathlib import Path
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import issues as ISS
from normalize import RULES
from analyze import PROFILES

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / 'data'
OUT = HERE / 'Louisville_Comparison_Validated.xlsx'

F = 'Arial'
H = Font(name=F, bold=True, color='FFFFFF')
HF = PatternFill('solid', fgColor='1F4E78')
SUB = PatternFill('solid', fgColor='D9E1F2')
GRY = PatternFill('solid', fgColor='F2F2F2')
YEL = PatternFill('solid', fgColor='FFF2CC')
B = Font(name=F, bold=True)
N = Font(name=F)
I = Font(name=F, italic=True, color='595959')
T = Font(name=F, bold=True, size=14)
USD = '$#,##0.00;($#,##0.00);"-"'
USD0 = '$#,##0;($#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
X = '0.00"x"'
thin = Side(style='thin', color='BFBFBF')

prof = pd.read_csv(DATA / 'profile_prices_all.csv', low_memory=False)
struct = pd.read_csv(DATA / 'structure_by_company.csv')
comp = pd.read_csv(DATA / 'companies.csv')
avail = pd.read_csv(DATA / 'price_availability.csv')
extras = pd.read_csv(DATA / 'extras.csv')
scope = pd.read_csv(DATA / 'scope.csv')
cov = pd.read_csv(DATA / 'city_coverage.csv')
norm_counts = pd.read_csv(DATA / 'rule_counts.csv')
ana = pd.read_csv(DATA / 'analytical_prices.csv.gz', low_memory=False)
issues, corrections, dictionary, tiers = ISS.frames()

wb = Workbook()


def hdr(ws, row, cols, start=1, fill=HF, font=H):
    for i, c in enumerate(cols):
        cell = ws.cell(row=row, column=start + i, value=c)
        cell.font, cell.fill = font, fill
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


def table(ws, df, start_row=1, money=(), pct=(), ratio=(), wrap=(), freeze=True, width=None):
    hdr(ws, start_row, list(df.columns))
    for r, row in enumerate(df.itertuples(index=False), start_row + 1):
        for c, v in enumerate(row, 1):
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                v = None if np.isnan(v) else 'open-ended'
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = N
            name = df.columns[c - 1]
            if name in money:
                cell.number_format = USD
            elif name in pct:
                cell.number_format = PCT
            elif name in ratio:
                cell.number_format = X
            if name in wrap:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    if freeze:
        ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    ws.auto_filter.ref = f'A{start_row}:{get_column_letter(len(df.columns))}{start_row + len(df)}'
    if width:
        widths(ws, width)
    else:
        for i, name in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(i)].width = min(60, max(10, len(str(name)) + 2))
    ws.row_dimensions[start_row].height = 42


# ============================================================================ README
ws = wb.active
ws.title = 'README'
ws['A1'] = 'Louisville Cleaning Prices - Validated Comparison (audit of the 13-14 Oct 2026 collection)'
ws['A1'].font = T
lines = [
    ('Built', '14 Oct 2026 from research/analysis/2026-10-14/data/*.csv (scripts in ./scripts). Original files untouched. No web collection, inquiries or bookings.'),
    ('Prices', 'Pre-tax US$ unless a cell note says otherwise. Blank or "n/o" = not offered or not captured; "n/m" = the form has no option that exactly matches the home. Missing prices are never shown as $0.'),
    ('Evidence', 'Every company column states its evidence tier (Evidence Tiers sheet). Live form observations are the strongest; Launch27 feed calculations and reconstructed models are calculations; published lists/ranges are not quotes. Nothing here is an independently obtained quote.'),
    ('', ''),
    ('READY for business decisions', ''),
    ('1', 'Louisville standard one-time, recurring (displayed / ongoing) and deep-clean price levels for typical 2-4 bedroom homes from 5 instant-price companies (incl. Maid 2 Clean, added 14 Oct) + R&R model + published lists (Louisville Comparison).'),
    ('2', 'How Louisville competitors build prices: what bedrooms, bathrooms, sq ft, frequency and deep/move add (Louisville Price Changes, Extras).'),
    ('3', 'Pricing-structure patterns across 23 usable peer-city companies, as examples only (Peer Structure).'),
    ('', ''),
    ('NEEDS VERIFICATION before relying on it', ''),
    ('a', 'RESOLVED 14 Oct (live validation, research/validation/2026-10-14): Red Feather move-out = deep is genuine and pricing is sq-ft-only; move-out is one-time only.'),
    ('b', 'Launch27-calculated prices other than Super Cleaning (12 live checks) and Maid 2 Clean (9 live checks): peer-city feeds not seen on a live form; tax/fee treatment where a site shows one total; Maid 2 Clean terms say recurring discounts apply after the first visit but the feed shows 0%.'),
    ('c', 'City / service-area assignment for peer companies (only Louisville companies were reviewed by hand).'),
    ('d', 'Included tasks: captured 14 Oct for 17 Louisville companies in research/checklists/2026-10-14 (task matrix); WebFetch-derived cells need re-reading before quoting.'),
    ('e', 'Contact-gated Louisville companies (MaidPro, Merry Maids, The Maids, The Cleaning Authority, Maid in the Ville): no prices; requests drafted, unsubmitted (research/quote-requests/2026-10-14).'),
    ('', ''),
    ('Sheets', 'Louisville Comparison · Louisville Long · Louisville Price Changes · Scope & Extras · Peer Structure · City Coverage · Companies · Price Availability · Issues · Corrections · Rules · Evidence Tiers · Profiles · Data Dictionary · Louisville Prices'),
]
for i, (a, b) in enumerate(lines, 3):
    ws.cell(row=i, column=1, value=a).font = B
    c = ws.cell(row=i, column=2, value=b)
    c.font = N
    c.alignment = Alignment(wrap_text=True, vertical='top')
widths(ws, [30, 140])

# ============================================================================ Louisville Comparison
ws = wb.create_sheet('Louisville Comparison')
ws['A1'] = 'Louisville - same homes priced by every company with usable data (pre-tax)'
ws['A1'].font = T
ws['A2'] = ('The 5 instant-price columns feed the Low/Median/High/n formulas. Rocking Robins (first-time clean, labour-hour formula) and published lists/ranges are shown to the right and are NOT in the formulas. '
            '"n/o" = not offered or not captured; "n/m" = no exact option match on the form.')
ws['A2'].font = I
INSTANT = [('scrub-lou', 'Scrub Lou', 'live form (13 & 14 Oct, identical)'), ('maids-in-apron', 'Maids in Apron', 'live form; deep/move = model from live add-on checks'),
           ('super-cleaning-louisville', 'Super Cleaning', 'Launch27 feed calc + 12 live checks (13-14 Oct)'), ('redfeathercleaning', 'Red Feather', 'live form (14 Oct; re-validated); sq-ft-only'),
           ('maid2cleanky', 'Maid 2 Clean', 'Launch27 feed calc + 9 live checks (14 Oct); whole baths only; no tax shown')]
PUB = [('rr-maids', 'Rocking Robins (R&R) - first clean only'), ('stitch', 'Stitch (published list)'), ('cleanoria', 'Cleanoria low (published)'), ('cleanoria', 'Cleanoria high (published)')]
lv = prof[prof.city == 'louisville']
CASES = [('Standard clean - one-time', 'standard', 'one_time', 'first'),
         ('Standard - weekly: displayed / first-visit price', 'standard', 'weekly', 'first'),
         ('Standard - weekly: ongoing visits (where shown separately or calculable)', 'standard', 'weekly', 'ongoing'),
         ('Standard - every 2 weeks: displayed / first-visit price', 'standard', 'biweekly', 'first'),
         ('Standard - every 2 weeks: ongoing visits', 'standard', 'biweekly', 'ongoing'),
         ('Standard - every 4 weeks: displayed / first-visit price', 'standard', 'every_4_weeks', 'first'),
         ('Standard - every 4 weeks: ongoing visits', 'standard', 'every_4_weeks', 'ongoing'),
         ('Deep clean - one-time', 'deep', 'one_time', 'first'),
         ('Move-in / move-out - one-time', 'move_in_out', 'one_time', 'first')]
r = 4
cols = ['Profile', 'Home', 'Beds', 'Baths', 'Sq ft'] + [n for _, n, _ in INSTANT] + ['Low', 'Median', 'High', 'n'] + [n for _, n in PUB]
first_inst, last_inst = 6, 5 + len(INSTANT)
stat_col = last_inst + 1
for title, svc, freq, which in CASES:
    ws.cell(row=r, column=1, value=title).font = Font(name=F, bold=True, size=12)
    r += 1
    hdr(ws, r, cols)
    r += 1
    # evidence row
    ws.cell(row=r, column=1, value='Evidence').font = I
    for j, (_, _, ev) in enumerate(INSTANT):
        c = ws.cell(row=r, column=first_inst + j, value=ev)
        c.font, c.alignment = I, Alignment(wrap_text=True)
    for j, lab in enumerate(['calculator formula (13 Oct, 1 live check)', 'published list (13 Oct)', 'Thumbtack FAQ range', 'Thumbtack FAQ range']):
        c = ws.cell(row=r, column=stat_col + 4 + j, value=lab)
        c.font, c.alignment = I, Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 40
    r += 1
    top = r
    for pid, plabel, bed, bath, sq in PROFILES:
        ws.cell(row=r, column=1, value=pid).font = N
        ws.cell(row=r, column=2, value=plabel).font = N
        ws.cell(row=r, column=3, value=bed).font = N
        ws.cell(row=r, column=4, value=bath).font = N
        c = ws.cell(row=r, column=5, value=sq)
        c.font, c.number_format = N, '#,##0'
        for j, (cid, _, _) in enumerate(INSTANT):
            x = lv[(lv.company_id == cid) & (lv.profile == pid) & (lv.service == svc) & (lv.frequency == freq)]
            col = first_inst + j
            if x.empty:
                v = 'n/o'
            else:
                x = x.iloc[0]
                v = x.first_visit_pretax if which == 'first' else x.ongoing_visit_pretax
                if pd.isna(v):
                    v = 'n/m' if str(x.status).startswith('no exact') or 'layout' in str(x.status) or 'gap' in str(x.status) or 'half bath' in str(x.status) else 'n/o'
            c = ws.cell(row=r, column=col, value=v)
            c.font, c.number_format = N, USD0
            if isinstance(v, str):
                c.alignment = Alignment(horizontal='center')
                c.font = I
        rng = f'{get_column_letter(first_inst)}{r}:{get_column_letter(last_inst)}{r}'
        for k, fn in enumerate(['MIN', 'MEDIAN', 'MAX']):
            c = ws.cell(row=r, column=stat_col + k, value=f'=IF(COUNT({rng})=0,"",{fn}({rng}))')
            c.font, c.number_format, c.fill = B, USD0, SUB
        c = ws.cell(row=r, column=stat_col + 3, value=f'=COUNT({rng})')
        c.font, c.fill = B, SUB
        # R&R + published (not in formulas)
        for j, (cid, name) in enumerate(PUB):
            x = lv[(lv.company_id == cid) & (lv.profile == pid) & (lv.service == svc) & (lv.frequency == freq)]
            if x.empty or which != 'first':
                v = 'n/o'
            else:
                x = x.iloc[0]
                v = x.first_visit_max if 'high' in name else x.first_visit_pretax
                if pd.isna(v):
                    v = 'n/m'
            c = ws.cell(row=r, column=stat_col + 4 + j, value=v)
            c.font, c.number_format, c.fill = N, USD0, GRY
            if isinstance(v, str):
                c.font = I
                c.alignment = Alignment(horizontal='center')
        r += 1
    r += 1
notes = [
    'Maids in Apron: every frequency charges full price on the first visit; ongoing visits are $20 / $15 / $10 lower (weekly / every 2 weeks / every 4 weeks). Displayed total includes 6% KY tax; divided by 1.06 here (matches 13 Oct live checks).',
    'Scrub Lou and Red Feather show one per-visit total for each frequency and do not say whether the first visit differs, so their "ongoing" cells are n/o.',
    'Super Cleaning (Launch27): discount applies to every visit including the first (feed: exclude_first = false). Live form adds 6% tax.',
    'Rocking Robins: first clean only (average condition, 1 story, no basement); the calculator does not price recurring visits; smallest layout is 2 bd / 2 ba.',
    'Red Feather move-in/out = deep-clean price; confirmed genuine by 22 live observations on 14 Oct (re-included). Move-out is offered one-time only; selecting a recurring schedule leaves the summary on One-Time.',
    'Maid 2 Clean (Launch27, smilesaremaid.launch27.com): bedroom service + $/bath (+ sq ft band for 3-4 bed); deep +$50, move +$99; 0% recurring discount in the feed, so first and ongoing are equal; the form shows no tax line. Half baths are not a form option (n/m).',
    'Stitch lists whole baths only (half baths priced as the lower whole number); Cleanoria figures are the published low/high of a range, not quotes.',
]
for t in notes:
    ws.cell(row=r, column=1, value='Note').font = B
    c = ws.cell(row=r, column=2, value=t)
    c.font = N
    r += 1
widths(ws, [8, 18, 6, 6, 8] + [16] * len(INSTANT) + [10, 10, 10, 5] + [17, 15, 14, 14])
ws.freeze_panes = 'F4'

# ============================================================================ Louisville Long
ws = wb.create_sheet('Louisville Long')
cols = ['company', 'evidence_tier', 'profile', 'profile_label', 'service', 'frequency', 'first_visit_pretax', 'first_visit_max', 'ongoing_visit_pretax',
        'recurring_basis', 'price_basis', 'status', 'matched_site_service', 'matched_sqft_label', 'source_file', 'source_row']
d = lv.reindex(columns=cols).sort_values(['company', 'profile', 'service', 'frequency'])
table(ws, d, money=('first_visit_pretax', 'first_visit_max', 'ongoing_visit_pretax'),
      width=[26, 34, 7, 34, 12, 13, 12, 12, 12, 40, 40, 34, 26, 20, 60, 9])

# ============================================================================ Louisville Price Changes
ws = wb.create_sheet('Louisville Price Changes')
ws['A1'] = 'How Louisville prices change (reference home 3 bd / 2 ba / 1,700 sq ft, standard one-time, pre-tax)'
ws['A1'].font = T
ws['A2'] = 'Each column changes one input from the reference home. Discounts: "displayed" = price shown for that frequency (first visit where shown separately); "ongoing" = later visits when shown or calculable.'
ws['A2'].font = I
s = struct[struct.city == 'louisville'].copy()
rr = prof[(prof.company_id == 'rr-maids')]
keep = ['company', 'price_varies_by', 'inputs_collected_but_not_priced', 'std_one_time', 'add_bedroom_3to4', 'add_full_bath_2to3', 'add_half_bath_2to2.5', 'add_1000_sqft_1700to2700',
        'weekly_first_visit_disc', 'weekly_ongoing_disc', 'biweekly_first_visit_disc', 'biweekly_ongoing_disc', 'every_4_weeks_first_visit_disc', 'every_4_weeks_ongoing_disc',
        'deep_one_time', 'deep_x_standard', 'move_in_out_one_time', 'move_in_out_x_standard']
s = s[keep].rename(columns={'std_one_time': 'standard one-time', 'add_bedroom_3to4': '+1 bedroom (3->4)', 'add_full_bath_2to3': '+1 full bath (2->3)',
                            'add_half_bath_2to2.5': '+half bath (2->2.5)', 'add_1000_sqft_1700to2700': '+1,000 sq ft (1,700->2,700)',
                            'weekly_first_visit_disc': 'weekly: displayed', 'weekly_ongoing_disc': 'weekly: ongoing', 'biweekly_first_visit_disc': 'every 2 wks: displayed',
                            'biweekly_ongoing_disc': 'every 2 wks: ongoing', 'every_4_weeks_first_visit_disc': 'every 4 wks: displayed', 'every_4_weeks_ongoing_disc': 'every 4 wks: ongoing',
                            'deep_one_time': 'deep one-time', 'deep_x_standard': 'deep / standard', 'move_in_out_one_time': 'move-out one-time', 'move_in_out_x_standard': 'move-out / standard'})
# MIA deep/move from model; R&R from formula; Maid 2 Clean from feed model; Red Feather move re-included 14 Oct
mia_deep = prof[(prof.company_id == 'maids-in-apron') & (prof.service == 'deep')]
def pv(cid, svc, bed, bath, sq):
    x = prof[(prof.company_id == cid) & (prof.service == svc) & (prof.bedrooms == bed) & (prof.bathrooms == bath) & (prof.sqft == sq) & (prof.frequency == 'one_time')]
    return x.first_visit_pretax.iloc[0] if len(x) else np.nan
table(ws, s, start_row=4, money=('standard one-time', '+1 bedroom (3->4)', '+1 full bath (2->3)', '+half bath (2->2.5)', '+1,000 sq ft (1,700->2,700)', 'deep one-time', 'move-out one-time'),
      pct=tuple(c for c in s.columns if ':' in c), ratio=('deep / standard', 'move-out / standard'), width=[30, 26, 22] + [13] * 15)
r = 6 + len(s)
for t in ['Maids in Apron deep / move-out at the reference home (13 Oct model): first visit = standard + bedroom-based add-on; 3 bedrooms: deep +$185, move +$210.',
          'Rocking Robins prices labour hours x $60: 3 bd / 2 ba = 7.5 h, +0.5 h for 1,500-2,000 sq ft, basic first clean -1 h (=$420), deep $480; 4 bd / 2 ba also 7.5 h (no bedroom step), 2-story +1 h, finished basement +1 h, heavy condition +1 h.',
          'Red Feather: bedroom and bathroom choices did not change the captured price (sq ft only). Treat as unconfirmed until checked on the live form.',
          'Add-on prices: Scope & Extras sheet.']:
    ws.cell(row=r, column=1, value='Note').font = B
    ws.cell(row=r, column=2, value=t).font = N
    r += 1

# ============================================================================ Scope & Extras
ws = wb.create_sheet('Scope & Extras')
ws['A1'] = 'Included tasks / checklists (what was actually captured)'
ws['A1'].font = T
table(ws, scope, start_row=3, wrap=tuple(scope.columns), freeze=False, width=[30, 40, 50, 50, 40])
r = 5 + len(scope)
ws.cell(row=r, column=1, value='Add-on prices (pre-tax). Louisville rows first. "per_unit" = priced per window/blind/room etc.').font = T
ex = extras.copy()
ex['order'] = (ex.city != 'Louisville').astype(int)
ex = ex.sort_values(['order', 'city', 'company', 'extra']).drop(columns='order')
table(ws, ex[['company', 'city', 'extra', 'price', 'per_unit', 'recurring_discount_applies', 'evidence_tier', 'services', 'source']], start_row=r + 1, money=('price',), freeze=False)
for i, w in enumerate([30, 40, 50, 50, 40, 30, 30, 14, 60], 1):
    ws.column_dimensions[get_column_letter(i)].width = w

# ============================================================================ Peer Structure
ws = wb.create_sheet('Peer Structure')
ws['A1'] = 'Pricing structure by company - peer cities (examples, not a market sample; do not convert to Louisville prices)'
ws['A1'].font = T
ws['A2'] = 'Reference home 3 bd / 2 ba / 1,700 sq ft. Summary rows use formulas over the company rows (blank = not available for that company).'
ws['A2'].font = I
ps = struct[struct.city != 'louisville'].copy()
ps['city'] = ps.city.str.replace('-', ' ').str.title()
keep2 = ['company', 'city', 'price_varies_by', 'inputs_collected_but_not_priced', 'std_one_time', 'add_bedroom_3to4', 'add_full_bath_2to3', 'add_half_bath_2to2.5',
         'add_1000_sqft_1700to2700', 'weekly_first_visit_disc', 'weekly_ongoing_disc', 'biweekly_first_visit_disc', 'biweekly_ongoing_disc',
         'every_4_weeks_first_visit_disc', 'every_4_weeks_ongoing_disc', 'deep_x_standard', 'move_in_out_x_standard', 'services_captured', 'frequencies_captured']
ps = ps[keep2].sort_values(['city', 'company'])
ps.columns = ['company', 'city', 'price varies by', 'inputs collected but not priced', 'standard one-time', '+1 bedroom', '+1 full bath', '+half bath', '+1,000 sq ft',
              'weekly: displayed', 'weekly: ongoing', 'every 2 wks: displayed', 'every 2 wks: ongoing', 'every 4 wks: displayed', 'every 4 wks: ongoing',
              'deep / standard', 'move-out / standard', 'services captured', 'frequencies captured']
table(ws, ps, start_row=4, money=('standard one-time', '+1 bedroom', '+1 full bath', '+half bath', '+1,000 sq ft'),
      pct=tuple(c for c in ps.columns if ':' in c), ratio=('deep / standard', 'move-out / standard'),
      width=[28, 14, 26, 22, 12, 11, 11, 11, 12, 11, 11, 11, 11, 11, 11, 11, 11, 30, 40])
top, bot = 5, 4 + len(ps)
r = bot + 2
for lab, fn in [('n (companies with a value)', 'COUNT'), ('Minimum', 'MIN'), ('Median', 'MEDIAN'), ('Maximum', 'MAX')]:
    ws.cell(row=r, column=1, value=lab).font = B
    for c in range(5, 18):
        L = get_column_letter(c)
        f = f'={fn}({L}{top}:{L}{bot})' if fn == 'COUNT' else f'=IF(COUNT({L}{top}:{L}{bot})=0,"",{fn}({L}{top}:{L}{bot}))'
        cell = ws.cell(row=r, column=c, value=f)
        cell.font, cell.fill = B, SUB
        cell.number_format = ws.cell(row=top, column=c).number_format if fn != 'COUNT' else '0'
    r += 1
r += 1
for t in ['Room-count example (feed rules only, not harvested): Spruced Up Cleans (Columbus, search-only city evidence) prices $40 base + $15/bedroom + $20/full bath + $10/half bath + $20/kitchen + $10/utility room + $16/other room; weekly 20%, every 2 weeks 15%, monthly 10% off.',
          'Excluded from this sheet: Deluxe Maid and Better Cleans (identical template prices), Fresh Space (Cleveland), Kindly (demo form), Maggy Maid (Airbnb only). Bear Bros, Divine Maids, Maid Cleaning Nashville and Rapids have no standard one-time price for the reference home.',
          '"displayed" discounts for single-total BookingKoala forms are on the per-visit price shown for that frequency; whether the first visit gets it is not stated.']:
    ws.cell(row=r, column=1, value='Note').font = B
    ws.cell(row=r, column=2, value=t).font = N
    r += 1

# ============================================================================ City Coverage / Companies / Availability / Issues / Corrections / Rules / Tiers / Profiles / Dictionary
ws = wb.create_sheet('City Coverage')
table(ws, cov, money=('ref_home_std_one_time_min', 'ref_home_std_one_time_median', 'ref_home_std_one_time_max'))
ws = wb.create_sheet('Companies')
table(ws, comp, wrap=('city_evidence', 'notes', 'capture_status'))
ws = wb.create_sheet('Price Availability')
table(ws, avail, wrap=('basis',))
ws = wb.create_sheet('Issues')
table(ws, issues, wrap=tuple(issues.columns), width=[6, 9, 16, 60, 70, 50, 22])
ws = wb.create_sheet('Corrections')
table(ws, corrections, wrap=tuple(corrections.columns), width=[45, 70, 70])
ws = wb.create_sheet('Rules')
table(ws, norm_counts, wrap=('rule_text',), width=[8, 90, 14, 14])
ws = wb.create_sheet('Evidence Tiers')
table(ws, tiers, wrap=('meaning',), width=[34, 120])
ws = wb.create_sheet('Profiles')
table(ws, pd.DataFrame(PROFILES, columns=['profile', 'description', 'bedrooms', 'bathrooms', 'sqft']), width=[8, 24, 10, 10, 10])
ws = wb.create_sheet('Data Dictionary')
table(ws, dictionary, wrap=('meaning',), width=[45, 40, 110])

# ============================================================================ Louisville Prices (analytical rows)
ws = wb.create_sheet('Louisville Prices')
lp = ana[ana.city == 'louisville'][['company', 'evidence_tier', 'service', 'site_service', 'frequency', 'frequency_raw', 'bedrooms', 'bathrooms', 'full_baths', 'half_baths',
                                    'sqft_label', 'price_first_or_per_visit', 'price_ongoing_visit', 'recurring_basis', 'price_basis', 'source_file', 'source_row']]
table(ws, lp, money=('price_first_or_per_visit', 'price_ongoing_visit'), width=[24, 30, 11, 30, 13, 22, 9, 9, 9, 9, 18, 12, 12, 30, 30, 55, 9])

for w in wb.worksheets:
    for row in w.iter_rows():
        for c in row:
            if c.font is None or c.font.name != F:
                c.font = Font(name=F, bold=c.font.bold, italic=c.font.italic, color=c.font.color, size=c.font.size)
wb.save(OUT)
print('saved', OUT)
