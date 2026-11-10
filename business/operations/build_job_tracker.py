"""Builds Job_Tracker_TEMPLATE.xlsx: a blank log for quotes, jobs and per-room times.

    pip install -r ../../requirements.txt
    python build_job_tracker.py

Copy the template to Job_Tracker.xlsx and fill that in. Job_Tracker.xlsx is git-ignored
because it holds customer and job details; never commit it. The Summary sheet compares
real cleaner-minutes with the estimates in ../pricing/Pricing_Model.xlsx and suggests
updated room prices. Open the file in Excel (or LibreOffice) so the formulas calculate.
"""
from pathlib import Path
from datetime import date, time
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().with_name("Job_Tracker_TEMPLATE.xlsx")
F = "Arial"
BLUE = Font(name=F, color="0000FF"); BLACK = Font(name=F); BOLD = Font(name=F, bold=True)
H1 = Font(name=F, bold=True, size=14); HDR = Font(name=F, bold=True, color="FFFFFF"); IT = Font(name=F, italic=True)
YEL = PatternFill("solid", fgColor="FFFF00"); HFILL = PatternFill("solid", fgColor="1F3A5F"); GREY = PatternFill("solid", fgColor="EEF1F4")
THIN = Side(style="thin", color="B0B7C0"); BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
USD = '$#,##0;($#,##0);-'; USD2 = '$#,##0.00;($#,##0.00);-'; PCT = '0%;-0%;-'; TIME = 'h:mm'; DATE = 'yyyy-mm-dd'; NUM = '0;-0;-'
NQ, NJ, NR = 300, 300, 2000   # rows prepared on the Quotes, Jobs and Room times sheets

# Room types, estimated cleaner-minutes and launch prices (keep in step with ../pricing/build_pricing_model.py)
ROOMS = [("Kitchen", 50, 55), ("Full bathroom", 35, 40), ("Half bathroom", 12, 15), ("Bedroom", 20, 20),
         ("Living / family room", 25, 30), ("Dining room", 15, 15), ("Office", 15, 15), ("Other room", 20, 20),
         ("Hallway / entry", 10, 10), ("Stairs", 12, 15),
         ("Add-on: change sheets", 8, 10), ("Add-on: inside oven", 40, 45), ("Add-on: inside fridge", 35, 45),
         ("Add-on: inside cabinets", 4, 5), ("Add-on: interior windows & tracks", 6, 8), ("Add-on: wet-wipe blinds", 5, 6)]
N_ROOM_TYPES = 10  # the first 10 are rooms (price follows minutes); the rest are add-ons (market-priced)

wb = Workbook()
def sheet(name, widths):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w
    return ws
def header(ws, row, labels, height=34):
    for i, l in enumerate(labels, 1):
        c = ws.cell(row, i, l); c.font = HDR; c.fill = HFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = height
    ws.freeze_panes = ws.cell(row + 1, 1)
def put(ws, ref, v, font=BLACK, fmt=None, fill=None):
    c = ws[ref]; c.value = v; c.font = font; c.border = BOX
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    return c
def dv_list(ws, formula, rng):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True); ws.add_data_validation(dv); dv.add(rng)

# ---------- Read me ----------
rm = wb.active; rm.title = "Read me"; rm.column_dimensions["A"].width = 118
for i, (t, f) in enumerate([
 ("Job tracker: quotes, jobs and room times", H1),
 ("Copy this template to Job_Tracker.xlsx and fill that in. Job_Tracker.xlsx is git-ignored; never commit customer or job details.", BOLD),
 ("", BLACK),
 ("How to use", BOLD),
 ("1. Quotes: one row per quote given, whether or not it was booked. This gives the quote-to-booking rate.", BLACK),
 ("2. Jobs: one row per visit. Enter arrival and departure times, the number of cleaners, the price charged and paid travel minutes.", BLACK),
 ("3. Room times: one row per room (or add-on) per job. Start and finish come from the timestamps of the start and finish photos.", BLACK),
 ("   Enter how many cleaners worked in the room. Cleaner-minutes = minutes x cleaners.", BLACK),
 ("4. Summary: average real cleaner-minutes per room type against the estimate, and a suggested price once a room type has 5 or more timings.", BLACK),
 ("5. When the averages settle, type them into the blue minutes cells of pricing/Pricing_Model.xlsx (and the builder script) and update price-list.md.", BLACK),
 ("", BLACK),
 ("Editing", BOLD),
 ("Blue text = type here. Yellow fill = settings to keep in step with the pricing model. Black = formula; don't overwrite.", BLACK),
 ("Times are entered as clock times, e.g. 9:05 or 14:30. Use a customer ID, not a name or address.", BLACK),
 ("Row 2 of each log is an EXAMPLE. Overwrite or clear it before entering real data, so it doesn't count in the Summary.", BLACK),
 ("Rooms overlap in practice (spray the shower, clean the kitchen while it soaks), so photo times run a little long for bathrooms. Averages over many jobs are what matter.", BLACK),
], 1):
    c = rm.cell(i, 1, t); c.font = f; c.alignment = Alignment(wrap_text=True)

# ---------- Summary (built first so other sheets can reference its settings) ----------
sm = sheet("Summary", [36, 14, 12, 16, 14, 14, 16, 44])
sm["A1"] = "Settings (keep in step with pricing/Pricing_Model.xlsx, Inputs sheet)"; sm["A1"].font = BOLD
settings = [("Price per cleaner-minute", 1.10, USD2), ("Price rounding ($)", 5, USD), ("Cleaner wage ($/hour)", 18, USD2),
            ("Payroll load (taxes, workers' comp)", 0.15, PCT), ("Supplies per visit ($)", 8, USD2), ("Card processing (% of price)", 0.03, PCT),
            ("Timings needed before suggesting a price", 5, NUM)]
for r, (lab, v, fmt) in enumerate(settings, 2):
    put(sm, f"A{r}", lab); put(sm, f"B{r}", v, BLUE, fmt, YEL)
put(sm, "A9", "Loaded labour cost per cleaner-minute", BOLD); put(sm, "B9", "=B4*(1+B5)/60", BLACK, USD2)
RATE, RND, LCOST, SUPP, CARD, NMIN = "Summary!$B$2", "Summary!$B$3", "Summary!$B$9", "Summary!$B$6", "Summary!$B$7", "Summary!$B$8"

# ---------- Lists ----------
ls = sheet("Lists", [36, 16, 18, 26])
header(ls, 1, ["Room / add-on type", "Yes / No", "Frequency", "Visit outcome"])
for i, (n, _, _) in enumerate(ROOMS, 2): ls.cell(i, 1, n).font = BLACK
for i, v in enumerate(["Y", "N"], 2): ls.cell(i, 2, v).font = BLACK
for i, v in enumerate(["One-time", "Weekly", "Every 2 weeks", "Every 4 weeks"], 2): ls.cell(i, 3, v).font = BLACK
for i, v in enumerate(["Complete", "Incomplete service"], 2): ls.cell(i, 4, v).font = BLACK
ROOMLIST = f"Lists!$A$2:$A${1 + len(ROOMS)}"

# ---------- Quotes ----------
qt = sheet("Quotes", [12, 12, 20, 10, 34, 14, 16, 10, 30, 30])
header(qt, 1, ["Date", "Quote ID", "How they found us", "ZIP", "Rooms / add-ons quoted", "Quoted price (pre-tax)", "Frequency", "Booked? (Y/N)", "Reason if not booked", "Notes"])
ex = [date(2026, 11, 16), "Q-EXAMPLE", "Nextdoor", "40217", "Kitchen, 2 full baths, 3 bedrooms, living, dining, hallway", 250, "Every 2 weeks", "Y", "", "Example row - overwrite"]
for j, v in enumerate(ex, 1):
    c = qt.cell(2, j, v); c.font = BLUE; c.border = BOX
qt["A2"].number_format = DATE; qt["F2"].number_format = USD
for r in range(3, NQ + 2):
    qt.cell(r, 1).number_format = DATE; qt.cell(r, 6).number_format = USD
    for j in range(1, 11): qt.cell(r, j).font = BLUE
dv_list(qt, "Lists!$C$2:$C$5", f"G2:G{NQ+1}"); dv_list(qt, "Lists!$B$2:$B$3", f"H2:H{NQ+1}")

# ---------- Jobs ----------
jb = sheet("Jobs", [12, 12, 12, 14, 9, 13, 9, 9, 10, 12, 11, 12, 12, 11, 10, 18, 30, 28])
header(jb, 1, ["Job ID", "Date", "Customer ID", "Frequency", "Visit # for this customer", "Price charged (pre-tax)", "Arrive", "Leave", "Cleaners",
               "Elapsed minutes", "Cleaner-min on site", "Paid travel cleaner-min", "Room cleaner-min (from Room times)",
               "Labour + supplies + card", "Margin $", "Margin %", "Visit outcome", "Issues / remedy offered", "Notes"], 48)
jb.column_dimensions["S"].width = 28
exj = {"A": "J-EXAMPLE", "B": date(2026, 11, 20), "C": "C-001", "D": "Every 2 weeks", "E": 1, "F": 250, "G": time(9, 0), "H": time(11, 5), "I": 2, "L": 30,
       "Q": "Complete", "S": "Example row - overwrite"}
for r in range(2, NJ + 2):
    for col in "ABCDEFGHILQRS":
        c = jb[f"{col}{r}"]; c.font = BLUE; c.border = BOX
        if r == 2 and col in exj: c.value = exj[col]
    jb[f"B{r}"].number_format = DATE; jb[f"F{r}"].number_format = USD; jb[f"G{r}"].number_format = TIME; jb[f"H{r}"].number_format = TIME
    put(jb, f"J{r}", f'=IF(OR(G{r}="",H{r}=""),"",ROUND((H{r}-G{r})*1440,0))', BLACK, NUM)
    put(jb, f"K{r}", f'=IF(OR(J{r}="",I{r}=""),"",J{r}*I{r})', BLACK, NUM)
    put(jb, f"M{r}", f"=IF(A{r}=\"\",\"\",SUMIFS('Room times'!$H$2:$H${NR+1},'Room times'!$A$2:$A${NR+1},A{r}))", BLACK, NUM)
    put(jb, f"N{r}", f'=IF(OR(K{r}="",F{r}=""),"",(K{r}+N(L{r}))*{LCOST}+{SUPP}+F{r}*{CARD})', BLACK, USD2)
    put(jb, f"O{r}", f'=IF(N{r}="","",F{r}-N{r})', BLACK, USD2)
    put(jb, f"P{r}", f'=IF(OR(N{r}="",N(F{r})=0),"",O{r}/F{r})', BLACK, PCT)
dv_list(jb, "Lists!$C$2:$C$5", f"D2:D{NJ+1}"); dv_list(jb, "Lists!$D$2:$D$3", f"Q2:Q{NJ+1}")

# ---------- Room times ----------
rt = sheet("Room times", [12, 34, 18, 10, 11, 11, 10, 12, 12, 36])
header(rt, 1, ["Job ID", "Room / add-on type", "Room label", "Cleaners in room", "Start photo time", "Finish photo time", "Minutes", "Cleaner-minutes",
               "Condition (O = ordinary, H = heavy)", "Notes"], 48)
exr = [("J-EXAMPLE", "Kitchen", "Kitchen", 1, time(9, 5), time(9, 58), "O", "Example rows - overwrite"),
       ("J-EXAMPLE", "Full bathroom", "Bath 1", 1, time(9, 5), time(9, 42), "O", ""),
       ("J-EXAMPLE", "Bedroom", "Bed 1", 1, time(9, 44), time(10, 3), "O", "")]
for r in range(2, NR + 2):
    for col in "ABCDEFIJ":
        c = rt[f"{col}{r}"]; c.font = BLUE; c.border = BOX
    rt[f"E{r}"].number_format = TIME; rt[f"F{r}"].number_format = TIME
    put(rt, f"G{r}", f'=IF(OR(E{r}="",F{r}=""),"",ROUND((F{r}-E{r})*1440,0))', BLACK, NUM)
    put(rt, f"H{r}", f'=IF(OR(G{r}="",D{r}=""),"",G{r}*D{r})', BLACK, NUM)
for r, row in enumerate(exr, 2):
    for col, v in zip("ABCDEFIJ", row): rt[f"{col}{r}"].value = v
dv_list(rt, ROOMLIST, f"B2:B{NR+1}")

# ---------- Summary tables ----------
header_row = 11
labels = ["Room / add-on type", "Estimated cleaner-min", "Times recorded", "Average actual cleaner-min", "Actual vs estimate", "Current price", "Suggested price", "Note"]
for i, l in enumerate(labels, 1):
    c = sm.cell(header_row, i, l); c.font = HDR; c.fill = HFILL; c.border = BOX; c.alignment = Alignment(wrap_text=True, vertical="center")
sm.row_dimensions[header_row].height = 34
TB, TH = f"'Room times'!$B$2:$B${NR+1}", f"'Room times'!$H$2:$H${NR+1}"
for k, (n, est, price) in enumerate(ROOMS):
    r = header_row + 1 + k
    put(sm, f"A{r}", n); put(sm, f"B{r}", est, BLUE, NUM); put(sm, f"F{r}", price, BLUE, USD)
    put(sm, f"C{r}", f'=COUNTIFS({TB},A{r},{TH},">0")', BLACK, NUM)
    put(sm, f"D{r}", f'=IF(C{r}=0,"",SUMIFS({TH},{TB},A{r})/C{r})', BLACK, '0.0')
    put(sm, f"E{r}", f'=IF(C{r}=0,"",D{r}/B{r}-1)', BLACK, '+0%;-0%;0%')
    if k < N_ROOM_TYPES:
        put(sm, f"G{r}", f'=IF(C{r}<{NMIN},"need more data",ROUND(D{r}*{RATE}/{RND},0)*{RND})', BLACK, USD)
        put(sm, f"H{r}", "Price follows minutes x price per cleaner-minute")
    else:
        put(sm, f"G{r}", f'=IF(C{r}<{NMIN},"need more data",D{r}*{LCOST})', BLACK, USD2)
        put(sm, f"H{r}", "Add-ons are market-priced; this is the labour cost per unit to check the price covers it")
k0 = header_row + len(ROOMS) + 3
sm[f"A{k0}"] = "Business numbers"; sm[f"A{k0}"].font = BOLD
QH, QF = f"Quotes!$H$2:$H${NQ+1}", f"Quotes!$F$2:$F${NQ+1}"
JF, JP, JQ, JK, JM = (f"Jobs!${c}$2:${c}${NJ+1}" for c in "FPQKM")
kpis = [("Quotes given", f'=COUNTA(Quotes!$B$2:$B${NQ+1})', NUM),
        ("Quotes booked", f'=COUNTIF({QH},"Y")', NUM),
        ("Quote-to-booking rate", f'=IF(B{k0+1}=0,"",B{k0+2}/B{k0+1})', PCT),
        ("Jobs logged", f'=COUNTA(Jobs!$A$2:$A${NJ+1})', NUM),
        ("Average price charged (pre-tax)", f'=IF(COUNT({JF})=0,"",AVERAGE({JF}))', USD),
        ("Average margin % (before overhead)", f'=IF(COUNT({JP})=0,"",AVERAGE({JP}))', PCT),
        ("Incomplete services", f'=COUNTIF({JQ},"Incomplete service")', NUM),
        ("Average cleaner-minutes on site per job", f'=IF(COUNT({JK})=0,"",AVERAGE({JK}))', '0'),
        ("Share of on-site time recorded in rooms", f'=IF(SUM({JK})=0,"",SUM({JM})/SUM({JK}))', PCT)]
for i, (lab, fml, fmt) in enumerate(kpis, 1):
    put(sm, f"A{k0+i}", lab); put(sm, f"B{k0+i}", fml, BLACK, fmt)
notes = ["Margin is before overhead (insurance, software, marketing, admin, owner pay) and before sales tax.",
         "If nearly every quote books, prices are probably low; if few do, price may be the obstacle. Change one thing at a time.",
         "On-site time not recorded in rooms is setup, packing, walking between rooms and the final walkthrough."]
for i, t in enumerate(notes):
    sm.cell(k0 + len(kpis) + 2 + i, 1, t).font = IT

wb._sheets = [wb[n] for n in ["Read me", "Summary", "Quotes", "Jobs", "Room times", "Lists"]]
wb.save(OUT); print(OUT)
