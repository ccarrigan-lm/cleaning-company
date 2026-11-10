"""Builds Pricing_Model.xlsx: launch room/area and add-on prices for our standard clean,
calibrated to the Louisville one-time standard-clean medians (14 Oct 2026), with recurring
discounts, sales tax and an editable labour-cost check.

    pip install -r ../../requirements.txt
    python build_pricing_model.py

Minutes and cost inputs are ESTIMATES until the job tracker has real times. To change a
price for good, change the value in this script and rebuild, so the workbook and the
script stay in step; then update ../price-list.md. Open the rebuilt file in Excel (or
LibreOffice) once so the formulas calculate."""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().with_name("Pricing_Model.xlsx")
F = "Arial"
BLUE = Font(name=F, color="0000FF"); BLACK = Font(name=F); GREEN = Font(name=F, color="008000")
BOLD = Font(name=F, bold=True); H1 = Font(name=F, bold=True, size=14); HDR = Font(name=F, bold=True, color="FFFFFF")
YEL = PatternFill("solid", fgColor="FFFF00"); HFILL = PatternFill("solid", fgColor="1F3A5F"); GREY = PatternFill("solid", fgColor="EEF1F4")
THIN = Side(style="thin", color="B0B7C0"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
USD = '$#,##0;($#,##0);-'; USD2 = '$#,##0.00;($#,##0.00);-'; PCT = '0%;(0%);-'

wb = Workbook()
def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    return ws
def header(ws, row, labels):
    for i, l in enumerate(labels, 1):
        c = ws.cell(row, i, l); c.font = HDR; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical="center"); c.border = BOX
    ws.row_dimensions[row].height = 32
def put(ws, ref, v, font=BLACK, fmt=None, fill=None, note=None):
    c = ws[ref]; c.value = v; c.font = font; c.border = BOX
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if note: c.comment = Comment(note, "pricing model")
    return c

# ---------- Read me ----------
rm = wb.active; rm.title = "Read me"; rm.column_dimensions["A"].width = 120
lines = [
 ("Pricing model: our standard clean (Louisville) - launch prices", H1),
 ("Status: launch prices. Prices are pre-tax unless a row says otherwise. Cleaner-minutes and cost inputs are estimates, not measured. Replace them with real job times from the job tracker; every price recalculates.", BOLD),
 ("", BLACK),
 ("How it works", BOLD),
 ("1. Each room/area has estimated cleaner-minutes for the full v5 standard-clean scope (Room prices sheet).", BLACK),
 ("2. Room price = minutes x price per cleaner-minute x market position, rounded to the nearest $5 (Inputs sheet).", BLACK),
 ("3. The price per cleaner-minute was calibrated so typical homes land at the Louisville median for a one-time standard clean (Market check sheet).", BLACK),
 ("4. Add-on prices are set from Louisville competitor add-on prices (Add-ons sheet).", BLACK),
 ("5. The minimum booking value is a price floor only; it adds no cleaning scope.", BLACK),
 ("6. Recurring visits: first visit at full price; later visits get the weekly / every-2-weeks / every-4-weeks discount (Inputs sheet). The minimum still applies.", BLACK),
 ("7. Sales tax (Kentucky 6%) is added on top of the pre-tax price in the Quote calculator.", BLACK),
 ("8. Labour cost check: wage, payroll load, setup, travel, supplies and card fees give a gross margin before overhead for each home (Market check sheet).", BLACK),
 ("", BLACK),
 ("Editing", BOLD),
 ("Blue text = input you can change. Yellow fill = key assumption to confirm. Black = formula. Green = link from another sheet.", BLACK),
 ("Use the Quote calculator sheet to price any home: enter room and add-on counts.", BLACK),
 ("", BLACK),
 ("Sources", BOLD),
 ("Market prices: research/analysis/2026-10-14/data/louisville_five_company_basis.csv (one-time standard clean, first visit, pre-tax; Scrub Lou, Maids in Apron, Super Cleaning, Red Feather, Maid 2 Clean; captured 13-14 Oct 2026; validated 14-15 Oct).", BLACK),
 ("Add-on prices: research/analysis/2026-10-14/data/extras.csv. Scope: business/service-checklist.md.", BLACK),
 ("Competitors' customer-facing hourly prices are $60-$65 per cleaner-hour (FINDINGS.md); the calibrated rate here is shown as $/cleaner-hour for comparison.", BLACK),
 ("", BLACK),
 ("Not in this model yet", BOLD),
 ("Overhead (insurance, software, marketing, admin, owner pay) and the four tasks left out of the launch standard clean (K7 full cabinet-front wash, B6 grout scrubbing, W5 stain/scuff removal, W6 full door wipe).", BLACK),
 ("Sales tax: Kentucky has taxed janitorial services, including residential cleaning, at 6% since 1 July 2018. Confirm registration and filing with an accountant.", BLACK),
]
for i, (t, f) in enumerate(lines, 1):
    c = rm.cell(i, 1, t); c.font = f; c.alignment = Alignment(wrap_text=True)

# ---------- Inputs ----------
inp = sheet("Inputs", [46, 14, 70])
header(inp, 1, ["Input", "Value", "Note / source"])
rows = [
 ("Price per cleaner-minute (base)", 1.10, USD2, True, "Calibrated: lands the 10 Louisville profiles at -10% to +6% of the market median (see Market check). Equals $66 per cleaner-hour; competitors show $60-$65 per cleaner-hour to customers."),
 ("Market position multiplier", 1.00, PCT, True, "100% = market median. E.g. 105% to price 5% above the median for our more thorough scope (wiped baseboards, microwave included)."),
 ("Price rounding ($)", 5, USD, False, "Room prices round to the nearest $5."),
 ("Minimum booking value ($)", 150, USD, True, "Price floor only, no added scope. Estimate: covers setup, travel and a small job with margin (see Market check row 'Minimum job')."),
 ("Cleaner wage ($/hour)", 18, USD2, True, "ASSUMPTION - replace with your actual pay rate."),
 ("Payroll load (taxes, workers' comp)", 0.15, PCT, True, "ASSUMPTION - confirm with payroll provider/insurer."),
 ("Setup + packing (cleaner-minutes per visit)", 20, None, False, "Estimate."),
 ("Travel (cleaner-minutes per visit, paid)", 30, None, False, "Estimate: e.g. 2 cleaners x 15 min."),
 ("Supplies per visit ($)", 8, USD2, False, "Estimate."),
 ("Card processing (% of price)", 0.03, PCT, False, "Estimate."),
 ("Recurring discount: weekly", 0.20, PCT, True, "From the 2nd visit. Most common Louisville / peer scheme is 20 / 15 / 10% (FINDINGS.md)."),
 ("Recurring discount: every 2 weeks", 0.15, PCT, True, "From the 2nd visit."),
 ("Recurring discount: every 4 weeks", 0.10, PCT, True, "From the 2nd visit."),
 ("Sales tax rate", 0.06, PCT, True, "Kentucky 6% on residential cleaning (janitorial services, taxable since 1 July 2018). Confirm with an accountant."),
]
for r, (lab, val, fmt, key, note) in enumerate(rows, 2):
    put(inp, f"A{r}", lab); put(inp, f"B{r}", val, BLUE, fmt, YEL if key else None); put(inp, f"C{r}", note)
    inp[f"C{r}"].alignment = Alignment(wrap_text=True)
put(inp, "A17", "Effective price per cleaner-minute", BOLD); put(inp, "B17", "=B2*B3", BLACK, USD2)
put(inp, "A18", "Effective price per cleaner-hour", BOLD); put(inp, "B18", "=B17*60", BLACK, USD)
put(inp, "A19", "Loaded labour cost per cleaner-minute", BOLD); put(inp, "B19", "=B6*(1+B7)/60", BLACK, USD2)
RATE, ROUNDV, MINB = "Inputs!$B$17", "Inputs!$B$4", "Inputs!$B$5"
LCOST, SETUP, TRAVEL, SUPP, CARD = "Inputs!$B$19", "Inputs!$B$8", "Inputs!$B$9", "Inputs!$B$10", "Inputs!$B$11"
DW, D2, D4, TAX = "Inputs!$B$12", "Inputs!$B$13", "Inputs!$B$14", "Inputs!$B$15"

# ---------- Room prices ----------
rp = sheet("Room prices", [28, 26, 14, 12, 16, 60])
header(rp, 1, ["Room / area", "Unit", "Est. cleaner-minutes", "Price", "Price per cleaner-hour", "Includes (v5 task IDs) / note"])
rooms = [
 ("Kitchen", "per kitchen", 50, "K1-K10 + every-room tasks (microwave, stovetop incl. ordinary grease, floor)"),
 ("Full bathroom", "per bathroom", 35, "B1-B9 (tub/shower incl. routine soap scum)"),
 ("Half bathroom", "per bathroom", 12, "B1, B3, B4, B5, B7-B9"),
 ("Bedroom", "per bedroom", 20, "R1-R6 (bed made with existing bedding)"),
 ("Living / family room", "per room", 25, "L1-L5"),
 ("Dining room", "per room", 15, "L1-L5"),
 ("Office", "per room", 15, "L1-L5"),
 ("Other room", "per room, up to ~250 sq ft", 20, "L1-L5; record use and size. Larger spaces count as 2."),
 ("Hallway / entry", "per area", 10, "W tasks + floor"),
 ("Stairs", "per flight", 12, "W9"),
]
for i, (n, u, m, note) in enumerate(rooms, 2):
    put(rp, f"A{i}", n); put(rp, f"B{i}", u); put(rp, f"C{i}", m, BLUE)
    put(rp, f"D{i}", f"=ROUND(C{i}*{RATE}/{ROUNDV},0)*{ROUNDV}", BLACK, USD)
    put(rp, f"E{i}", f"=IF(C{i}>0,D{i}/C{i}*60,0)", BLACK, USD); put(rp, f"F{i}", note)
RLAST = 1 + len(rooms)
rp["A13"] = "Every selected room also gets W1-W8 (fans, cobwebs, sills, blinds dusted, accessible baseboards wiped, switches, floors). Minutes are estimates for a normally maintained home; replace with real times from the job tracker."
rp["A13"].font = Font(name=F, italic=True)

# ---------- Add-ons ----------
ad = sheet("Add-ons", [32, 16, 14, 10, 14, 14, 54])
header(ad, 1, ["Add-on", "Unit", "Est. cleaner-minutes", "Price", "Labour + card cost", "Margin per unit", "Louisville competitor prices (pre-tax)"])
addons = [
 ("Change sheets", "per bed", 8, 10, "$10 Super Cleaning"),
 ("Inside oven", "each", 40, 45, "$45 Scrub Lou, $45 Maids in Apron, $65 Super Cleaning, $25 Maid 2 Clean"),
 ("Inside fridge", "each", 35, 45, "$45 Scrub Lou, $45 Maids in Apron, $65 Super Cleaning (fridge & freezer), $60 R&R, $25 Maid 2 Clean"),
 ("Inside cabinets (emptied by customer)", "per cabinet", 4, 5, "$5 per unit Maids in Apron, $20 Maid 2 Clean"),
 ("Interior windows & tracks", "per window", 6, 8, "$8 glass & tracks Scrub Lou, $8 Super Cleaning, $5 Maids in Apron / R&R"),
 ("Wet-wipe blinds", "per set", 5, 6, "$5 Maids in Apron / Maid 2 Clean, $20 R&R"),
]
for i, (n, u, m, p, ref) in enumerate(addons, 2):
    put(ad, f"A{i}", n); put(ad, f"B{i}", u); put(ad, f"C{i}", m, BLUE); put(ad, f"D{i}", p, BLUE, USD)
    put(ad, f"E{i}", f"=C{i}*{LCOST}+D{i}*{CARD}", BLACK, USD2); put(ad, f"F{i}", f"=D{i}-E{i}", BLACK, USD2); put(ad, f"G{i}", ref)
ALAST = 1 + len(addons)
ad["A9"] = "Add-on prices are set at or near the Louisville median; they are inputs, not calculated from minutes. Minutes are estimates."
ad["A9"].font = Font(name=F, italic=True)

# ---------- Market check ----------
mk = sheet("Market check", [34] + [8]*10 + [11, 10, 10, 11, 10, 9, 10, 11, 11, 11, 11, 10, 12, 12, 11])
cols = [r[0] for r in rooms]
H = ["Home profile (market)"] + cols + ["Cleaner-min (rooms)", "Our price", "Market median", "Ours vs median",
     "Scrub Lou", "Maids in Apron", "Super Cleaning", "Red Feather", "Maid 2 Clean", "Labour + supplies + card", "Gross margin $", "Gross margin %",
     "Our every-2-weeks price (2nd visit on)", "Market every-2-weeks ongoing median", "Ours vs median (2-wk)"]
header(mk, 1, H); mk.row_dimensions[1].height = 46
profiles = [  # label, room counts, five competitor prices, one-time median, every-2-weeks ongoing median
 ("P1 Apartment 1bd/1ba/750", [1,1,0,1,1,0,0,0,1,0], [169,165,170,175,142], 169, 142),
 ("P2 Small house 2bd/1ba/1,000", [1,1,0,2,1,0,0,0,1,0], [199,175,195,205,157], 195, 157),
 ("P3 Condo 2bd/2ba/1,200", [1,2,0,2,1,0,0,0,1,0], [219,190,230,205,174], 205, 174),
 ("P4 Starter 3bd/1.5ba/1,400", [1,1,1,3,1,0,0,0,1,0], [219,214,220,225,None], 219.5, 182),
 ("P5 Ranch 3bd/2ba/1,600", [1,2,0,3,1,1,0,0,1,0], [249,219,255,245,200], 245, 200),
 ("P6 2-story 3bd/2ba/1,900", [1,2,0,3,1,1,0,0,1,1], [249,219,255,265,200], 249, 200),
 ("P7 3bd/2.5ba/2,200", [1,2,1,3,1,1,0,0,1,1], [279,224,295,285,None], 282, 215.125),
 ("P8 4bd/2.5ba/2,500", [1,2,1,4,1,1,1,0,1,1], [309,294,325,325,None], 317, 261.375),
 ("P9 4bd/3ba/3,000", [1,3,0,4,1,1,1,0,2,1], [339,304,360,375,246], 339, 270),
 ("P10 5bd/3.5ba/3,800", [1,3,1,5,1,1,1,1,2,1], [379,434,415,415,None], 415, 365.125),
]
cnt = lambda r: f"B{r}:K{r}"
HM, HP = 16, 17  # helper rows: room minutes and prices laid out across B:K
minsT = f"$B${HM}:$K${HM}"
pricT = f"$B${HP}:$K${HP}"
for i, (lab, counts, comp, med, med2) in enumerate(profiles, 2):
    put(mk, f"A{i}", lab)
    for j, c in enumerate(counts): put(mk, f"{get_column_letter(2+j)}{i}", c, BLUE)
    put(mk, f"L{i}", f"=SUMPRODUCT(B{i}:K{i},{minsT})")
    put(mk, f"M{i}", f"=MAX({MINB},SUMPRODUCT(B{i}:K{i},{pricT}))", BLACK, USD)
    put(mk, f"N{i}", med, BLUE, USD)
    put(mk, f"O{i}", f"=M{i}/N{i}-1", BLACK, '+0%;-0%;0%')
    for j, v in enumerate(comp): put(mk, f"{get_column_letter(16+j)}{i}", v if v is not None else "n/m", BLUE, USD)
    put(mk, f"U{i}", f"=(L{i}+{SETUP}+{TRAVEL})*{LCOST}+{SUPP}+M{i}*{CARD}", BLACK, USD)
    put(mk, f"V{i}", f"=M{i}-U{i}", BLACK, USD); put(mk, f"W{i}", f"=IF(M{i}>0,V{i}/M{i},0)", BLACK, PCT)
    put(mk, f"X{i}", f"=MAX({MINB},M{i}*(1-{D2}))", BLACK, USD); put(mk, f"Y{i}", med2, BLUE, USD)
    put(mk, f"Z{i}", f"=X{i}/Y{i}-1", BLACK, '+0%;-0%;0%')
PL = 1 + len(profiles); r = PL + 1
put(mk, f"A{r}", "Minimum job (e.g. 1 full bath + 1 bedroom)", BOLD)
for j, c in enumerate([0,1,0,1,0,0,0,0,0,0]): put(mk, f"{get_column_letter(2+j)}{r}", c, BLUE)
put(mk, f"L{r}", f"=SUMPRODUCT(B{r}:K{r},{minsT})")
put(mk, f"M{r}", f"=MAX({MINB},SUMPRODUCT(B{r}:K{r},{pricT}))", BLACK, USD)
put(mk, f"U{r}", f"=(L{r}+{SETUP}+{TRAVEL})*{LCOST}+{SUPP}+M{r}*{CARD}", BLACK, USD)
put(mk, f"V{r}", f"=M{r}-U{r}", BLACK, USD); put(mk, f"W{r}", f"=IF(M{r}>0,V{r}/M{r},0)", BLACK, PCT)
s = r + 2
put(mk, f"A{s}", "Average ours vs median (P1-P10)", BOLD); put(mk, f"O{s}", f"=AVERAGE(O2:O{PL})", BLACK, '+0%;-0%;0%')
put(mk, f"A{s+1}", "Lowest / highest ours vs median", BOLD); put(mk, f"O{s+1}", f"=MIN(O2:O{PL})", BLACK, '+0%;-0%;0%'); put(mk, f"P{s+1}", f"=MAX(O2:O{PL})", BLACK, '+0%;-0%;0%')
put(mk, f"A{HM}", "Helper: est. cleaner-minutes per room", BOLD)
put(mk, f"A{HP}", "Helper: price per room", BOLD)
for j in range(len(rooms)):
    col = get_column_letter(2 + j)
    put(mk, f"{col}{HM}", f"='Room prices'!C{2+j}", GREEN)
    put(mk, f"{col}{HP}", f"='Room prices'!D{2+j}", GREEN, USD)
s += 4
notes = [
 "Market = one-time standard clean, first visit, pre-tax (louisville_five_company_basis.csv). n/m = no matching option. Median is the five-company median (four where one is n/m).",
 "Room counts per profile are ASSUMPTIONS: every home has a kitchen, living room and one hallway/entry; 1,600+ sq ft adds a dining room; 2-story homes add one flight of stairs; 2,500+ adds an office; 3,000+ adds a second hallway; 3,800 adds one Other room. 2.5 baths = 2 full + 1 half.",
 "Gross margin is before overhead (insurance, software, marketing, admin, owner pay) and before sales tax. It is for the first / one-time visit.",
 "Every-2-weeks market median = ongoing (later) visits, pre-tax, from only 2-3 companies per profile (the others show one price), so treat it as a rough guide.",
]
for k, t in enumerate(notes):
    c = mk.cell(s + 3 + k, 1, t); c.font = Font(name=F, italic=True)
mk.freeze_panes = "B2"

# ---------- Quote calculator ----------
qc = sheet("Quote calculator", [36, 12, 12, 14])
header(qc, 1, ["Room / area or add-on", "Count", "Unit price", "Line total"])
row = 2
for i in range(2, RLAST + 1):
    put(qc, f"A{row}", f"='Room prices'!A{i}", GREEN); put(qc, f"B{row}", 0, BLUE, None, YEL)
    put(qc, f"C{row}", f"='Room prices'!D{i}", GREEN, USD); put(qc, f"D{row}", f"=B{row}*C{row}", BLACK, USD); row += 1
for i in range(2, ALAST + 1):
    put(qc, f"A{row}", f"='Add-ons'!A{i}&\" (\"&'Add-ons'!B{i}&\")\"", GREEN); put(qc, f"B{row}", 0, BLUE, None, YEL)
    put(qc, f"C{row}", f"='Add-ons'!D{i}", GREEN, USD); put(qc, f"D{row}", f"=B{row}*C{row}", BLACK, USD); row += 1
last = row - 1
# example: typical ranch
for k, v in {2: 1, 3: 2, 5: 3, 6: 1, 7: 1, 10: 1}.items(): qc[f"B{k}"].value = v
put(qc, f"A{row+1}", "Subtotal", BOLD); put(qc, f"D{row+1}", f"=SUM(D2:D{last})", BLACK, USD)
put(qc, f"A{row+2}", "Minimum booking value", BOLD); put(qc, f"D{row+2}", f"={MINB}", GREEN, USD)
B_ = Font(name=F, bold=True)
put(qc, f"A{row+3}", "One-time / first visit price (pre-tax)", BOLD); put(qc, f"D{row+3}", f"=IF(D{row+1}=0,0,MAX(D{row+1},D{row+2}))", B_, USD)
put(qc, f"A{row+4}", "Sales tax", BOLD); put(qc, f"D{row+4}", f"=D{row+3}*{TAX}", BLACK, USD2)
put(qc, f"A{row+5}", "Customer pays (first visit)", BOLD); put(qc, f"D{row+5}", f"=D{row+3}+D{row+4}", B_, USD2)
put(qc, f"A{row+7}", "Recurring visits, from the 2nd visit (pre-tax)", BOLD)
for k, (lab, d) in enumerate([("Weekly", DW), ("Every 2 weeks", D2), ("Every 4 weeks", D4)]):
    rr = row + 8 + k
    put(qc, f"A{rr}", lab); put(qc, f"C{rr}", f"={d}", GREEN, PCT)
    put(qc, f"D{rr}", f"=IF(D{row+1}=0,0,MAX(D{row+2},D{row+1}*(1-{d})))", BLACK, USD2)
qc.cell(row + 12, 1, "Enter counts in the yellow cells. Example filled in: typical ranch (kitchen, 2 full baths, 3 bedrooms, living, dining, hallway). The recurring discount applies to the whole visit; the minimum booking value still applies.").font = Font(name=F, italic=True)

wb.save(OUT); print(OUT)
