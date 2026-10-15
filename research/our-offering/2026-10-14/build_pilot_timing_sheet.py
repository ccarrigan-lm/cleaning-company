"""Builds PILOT_TIMING_SHEET.pdf, the blank printable timing sheet used with
STANDARD_CLEAN_CHECKLIST_v5.md during paid pilot cleans.

Regenerate (from this folder):
    pip install -r requirements.txt
    python build_pilot_timing_sheet.py

The PDF is written next to this script. Use only characters that ReportLab's
built-in Helvetica can draw (no check marks, ballot boxes or middle dots).
Prices stay TBD; the sheet holds no personal details.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

OUT = str(Path(__file__).resolve().with_name("PILOT_TIMING_SHEET.pdf"))
W, H = landscape(letter)
M = 0.4*inch
doc = SimpleDocTemplate(OUT, pagesize=(W, H), leftMargin=M, rightMargin=M, topMargin=0.4*inch, bottomMargin=0.45*inch,
                        title="Pilot Timing Sheet", author="Standard clean pilot")
CW = W - 2*M
INK = colors.HexColor("#1f2933"); GRID = colors.HexColor("#8a94a0"); SHADE = colors.HexColor("#e8ecf0"); NOTE = colors.HexColor("#4a5560")

h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=INK)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK, spaceBefore=6, spaceAfter=3)
body = ParagraphStyle("b", fontName="Helvetica", fontSize=8, leading=10, textColor=INK)
small = ParagraphStyle("s", fontName="Helvetica", fontSize=7, leading=8.6, textColor=NOTE)
th = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7, leading=8.4, textColor=INK)
td = ParagraphStyle("td", fontName="Helvetica", fontSize=7, leading=8.4, textColor=INK)
P = lambda t, s=td: Paragraph(t, s)

def grid(data, widths, row_h=None, header_rows=1, extra=()):
    t = Table(data, colWidths=widths, rowHeights=row_h, repeatRows=header_rows)
    st = [("GRID", (0,0), (-1,-1), 0.5, GRID),
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
          ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
          ("TOPPADDING", (0,0), (-1,-1), 2), ("BOTTOMPADDING", (0,0), (-1,-1), 2)]
    if header_rows: st.append(("BACKGROUND", (0,0), (-1,header_rows-1), SHADE))
    t.setStyle(TableStyle(st + list(extra)))
    return t

def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(NOTE)
    c.drawString(M, 0.25*inch, "Pilot timing sheet | use with STANDARD_CLEAN_CHECKLIST_v5.md (full task instructions are there) | prices TBD | no personal details go in the Git repo")
    c.drawRightString(W-M, 0.25*inch, f"Pilot home ___ of 3 | page {d.page}")
    c.restoreState()

s = []
s.append(P("Pilot timing sheet: standard clean", h1))
s.append(P("<b>Paid pilot.</b> The goal is to finish every task to the checklist standard. Do not rush to meet an estimate: cleaners are paid for actual time, and estimates are recorded only to see how far off they were. "
           "Pilot home 1 is the owner's home.", body))
s.append(Spacer(1, 5))

info = [
 [P("<b>Pilot home</b>  1 / 2 / 3"), P("<b>Date</b>"), P("<b>Home ID</b> (no address)"), P("<b>Pets present?</b>  Y / N"), P("<b>Photo permission?</b>  Y / N")],
 [P("<b>Clock start</b>"), P("<b>Clock finish</b>"), P("<b>Elapsed minutes</b> (finish - start)"), P("<b>Number of cleaners</b>"), P("<b>Cleaners</b> (initials)")],
]
s.append(grid(info, [CW/5]*5, row_h=[20, 20], header_rows=0))
s.append(Spacer(1, 3))
s.append(P("<b>Cleaner-minutes</b> = minutes each cleaner spent, added together. Two cleaners working 30 minutes in a room = 30 elapsed minutes but <b>60 cleaner-minutes</b>. "
           "Every time column below is in cleaner-minutes, except elapsed time above.", small))

s.append(P("1. Rooms and areas (selected rooms only)", h2))
ref = ("<b>Task IDs.</b> Kitchen K1–K10 | Full bath B1–B9 | Half bath B1, B3, B4, B5, B7–B9 | Bedroom R1–R6 | Living/dining/family and Office L1–L5 | "
       "Other room L1–L5 (record use and size) | Hallway/entry/stairs W9 | <b>Every selected room</b> W1–W8, plus W10 at the end. "
       "<b>Floor minutes are part of the room's total, not added to it.</b>  Condition: O = ordinary, H = heavy (H must be disclosed and quoted to count as agreed work).")
s.append(P(ref, small)); s.append(Spacer(1, 3))
hdr = ["Room / area<br/>(type; use if Other)", "Approx size<br/>(sq ft)", "Floor type<br/>(carpet / hard / mixed)", "Starting<br/>condition<br/>O / H + note",
       "Est.<br/>cleaner-min<br/>(room total)", "Actual<br/>cleaner-min<br/>(room total)", "of which<br/>floor min", "Quality check<br/>(OK or issue)",
       "Not completed / missed<br/>(task ID + reason)"]
wid = [1.35, 0.7, 0.85, 0.95, 0.75, 0.75, 0.65, 1.1, 2.9]
k = CW / sum(wid); wid = [w*k for w in wid]
rows = [[P(h, th) for h in hdr]] + [[""]*9 for _ in range(11)]
rows.append([P("<b>Rooms total</b>", th), "", "", "", "", "", "", "", ""])
s.append(grid(rows, wid, row_h=[34] + [22]*11 + [18],
              extra=[("BACKGROUND", (0,12), (-1,12), SHADE), ("SPAN", (0,12), (3,12)),
                     ("BACKGROUND", (7,12), (-1,12), SHADE)]))
s.append(P("Use one row per room. If a room needs more time to reach the standard, keep going and record the actual minutes.", small))

s.append(PageBreak())
s.append(P("2. Ordinary vs heavy: K3 stovetop, K5 microwave, B2 tub/shower", h2))
s.append(P("These minutes are already included in the room totals in section 1. They're broken out here so the condition examples can be built. Photograph only with permission.", small))
s.append(Spacer(1, 3))
cond = [[P(x, th) for x in ["Task", "Room", "Condition O / H", "Disclosed & quoted? Y / N", "Cleaner-min for this task", "Photo # (if permitted)", "What made it heavy / notes"]]]
for t_ in ["K3 stovetop", "K5 microwave", "B2 tub/shower", "B2 tub/shower", "B2 tub/shower"]:
    cond.append([P(t_), "", "", "", "", "", ""])
cw = [1.0, 0.9, 0.9, 1.1, 1.0, 0.9, 3.6]; k = CW/sum(cw); cw = [w*k for w in cw]
s.append(grid(cond, cw, row_h=[20]+[18]*5))

s.append(P("3. Add-ons selected for this visit, and non-room time", h2))
ad = [[P(x, th) for x in ["Item", "Qty / unit", "Selected? Y / N", "Est. cleaner-min", "Actual cleaner-min", "Notes / quality"]]]
for name, unit in [("Change sheets", "beds"), ("Inside oven", "ovens"), ("Inside fridge", "fridges"), ("Inside cabinets (emptied by customer)", "cabinets"),
                   ("Interior windows & tracks", "windows"), ("Wet-wipe blinds", "sets")]:
    ad.append([P(name), P(f"____ {unit}"), "", "", "", ""])
ad.append([P("<b>Add-ons total</b>", th), "", "", "", "", ""])
for name in ["Setup (arrive, unload, walk-through)", "Packing (pack up, load)", "Travel to home (per cleaner)", "Travel from home (per cleaner)"]:
    ad.append([P(name), "", P("—"), "", "", ""])
aw = [2.2, 0.9, 0.9, 1.0, 1.0, 3.3]; k = CW/sum(aw); aw = [w*k for w in aw]
s.append(grid(ad, aw, row_h=[20]+[17]*6+[16]+[17]*4,
              extra=[("BACKGROUND", (0,7), (-1,7), SHADE), ("LINEABOVE", (0,8), (-1,8), 1.2, INK)]))

s.append(P("4. Visit totals", h2))
tot = [[P(x, th) for x in ["", "Estimated", "Actual"]],
       [P("<b>A.</b> Standard-clean cleaner-minutes on site: rooms (sec. 1) + add-ons (sec. 3) + setup + packing"), "", ""],
       [P("<b>B.</b> Scope-review cleaner-minutes (sec. 5): kept out of A, but paid work"), P("-"), ""],
       [P("<b>C.</b> Pilot walkthrough and feedback cleaner-minutes (explaining the checklist, estimating, debrief)"), P("-"), ""],
       [P("<b>D.</b> Travel cleaner-minutes (to + from, sec. 3)"), "", ""],
       [P("<b>Total paid pilot labour = A + B + C + D</b> (cleaner-minutes)", th), P("-"), ""],
       [P("Elapsed (clock) minutes on site, from page 1"), "", ""]]
s.append(grid(tot, [CW*0.6, CW*0.2, CW*0.2], row_h=[16, 18, 18, 18, 18, 18, 18],
              extra=[("BACKGROUND", (0,5), (-1,5), SHADE), ("LINEABOVE", (0,5), (-1,5), 1.2, INK)]))
s.append(P("Room and add-on costs are built from A. B, C and D are still paid and count in total pilot labour.", small))

s.append(PageBreak())
s.append(P("5. Scope-review tasks: undecided, observe and time separately", h2))
s.append(P("These four tasks are <b>not decided</b>: they're not part of the standard clean, not add-ons, and not excluded. Record what you see. "
           "Do a task only if the homeowner agrees for this pilot, and time it separately. <b>Don't include these minutes in room totals.</b> They are still paid work and count in total pilot labour (sec. 4, line B).", small))
s.append(Spacer(1, 3))
sr = [[P(x, th) for x in ["Task (still undecided)", "Need observed: none / some / heavy", "Where (rooms)", "Done in pilot? Y / N", "Incremental cleaner-min", "Observations"]]]
for t_ in ["K7: full wash of every cabinet front", "B6: scrubbing grout lines", "W5: baseboard stain / scuff removal", "W6: full wipe of doors and frames"]:
    sr.append([P(t_), "", "", "", "", ""])
sw = [2.0, 1.3, 1.3, 0.9, 1.0, 3.5]; k = CW/sum(sw); sw = [w*k for w in sw]
s.append(grid(sr, sw, row_h=[20]+[24]*4))

s.append(P("6. Completion and quality check", h2))
q = [[P("<b>Final walkthrough (W10) done by:</b>"), P("<b>Checked against the checklist by:</b>")],
     [P("<b>Visit outcome:</b>   Complete   /   Incomplete service (agreed work left unfinished, including running out of time)"),
      P("<b>Anything missed after the quality check?</b> (task ID, room, fixed on site Y / N)")]]
s.append(grid(q, [CW/2, CW/2], row_h=[18, 40], header_rows=0))
s.append(P("A not-completed reason is a record, not a decision: the office reviews every not-completed item against the agreed scope (rule 9).", small))

s.append(P("7. Unclear instructions and cleaner feedback", h2))
fb = [[P(x, th) for x in ["Task ID", "What was unclear or didn't work", "Suggested wording or change"]]] + [[""]*3 for _ in range(4)]
s.append(grid(fb, [CW*0.1, CW*0.5, CW*0.4], row_h=[14]+[20]*4))
s.append(Spacer(1, 4))
gen = [[P("<b>Cleaner feedback</b> (pace, equipment, supplies, anything that would make the standard easier to hit):")]]
s.append(grid(gen, [CW], row_h=[46], header_rows=0))

s.append(P("8. Reach equipment agreed with the cleaners (internal, not for customer wording)", h2))
re_ = [[P("[  ] Extension duster   length ____"), P("[  ] Extension pole   length ____"), P("[  ] Step stool   ____ steps / height ____"), P("[  ] Other: ________________")],
       [P("<b>Safe-use rules agreed:</b>"), "", "", ""]]
s.append(grid(re_, [CW/4]*4, row_h=[18, 30], header_rows=0, extra=[("SPAN", (0,1), (-1,1))]))
s.append(P("Never stand or climb on furniture, counters, tubs or fixtures (rule 1). Anything not safely reachable is recorded as not completed: beyond safe reach.", small))

doc.build(s, onFirstPage=footer, onLaterPages=footer)
print("ok")
