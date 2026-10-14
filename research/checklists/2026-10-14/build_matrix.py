"""Build the Louisville task-by-company scope matrix from the 14 Oct 2026 published checklists.

Rules (from the request): code only what a company's own pages say. Silence = "not stated", never "excluded".
A task one company calls "deep" is NOT assumed to be in anyone else's deep clean.

Status codes
  INC  explicitly included in that service tier
  EXC  explicitly excluded (company-wide refusal, or a checklist that marks the task as not part of that tier)
  PAID offered as a paid extra / add-on (price where published or captured from the booking form)
  COND included only on request, "as needed", "if provided", "if accessible", or with another stated condition
  NS   not stated for that tier
Each cell carries the supporting text and the source file in raw/.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATE = '2026-10-14'

TASKS = [
    ('Kitchen', 'counters', 'Counters & backsplash'),
    ('Kitchen', 'k_sink', 'Kitchen sink'),
    ('Kitchen', 'stovetop', 'Stovetop / range top'),
    ('Kitchen', 'appl_ext', 'Appliance exteriors'),
    ('Kitchen', 'micro_in', 'Inside microwave'),
    ('Kitchen', 'cab_fronts', 'Cabinet fronts'),
    ('Kitchen', 'hood', 'Range hood / hood vent'),
    ('Kitchen', 'cab_in', 'Inside cabinets & drawers'),
    ('Kitchen', 'fridge_in', 'Inside fridge / freezer'),
    ('Kitchen', 'oven_in', 'Inside oven'),
    ('Kitchen', 'dishes', 'Dishes (load / wash / put away)'),
    ('Bathroom', 'toilet', 'Toilet'),
    ('Bathroom', 'tub_shower', 'Tub & shower'),
    ('Bathroom', 'b_sink', 'Bathroom sink, counter & fixtures'),
    ('Bathroom', 'mirrors', 'Mirrors & glass'),
    ('Bathroom', 'grout', 'Scrub tile grout'),
    ('Bathroom', 'soap_scum', 'Heavy soap-scum / hard-water removal'),
    ('Whole home', 'dust', 'Dust reachable surfaces & furniture'),
    ('Whole home', 'fans', 'Ceiling fans'),
    ('Whole home', 'fixtures', 'Light fixtures'),
    ('Whole home', 'cobwebs', 'Cobwebs'),
    ('Whole home', 'bb_dust', 'Baseboards – dusted'),
    ('Whole home', 'bb_wipe', 'Baseboards – hand-wiped / washed'),
    ('Whole home', 'sills', 'Window sills & ledges'),
    ('Whole home', 'blinds', 'Blinds'),
    ('Whole home', 'doors', 'Doors & door frames wiped'),
    ('Whole home', 'switches', 'Light switches & door handles'),
    ('Whole home', 'win_in', 'Interior window glass'),
    ('Whole home', 'win_out', 'Exterior windows'),
    ('Whole home', 'walls', 'Spot-clean walls'),
    ('Whole home', 'vents', 'Air vents / returns'),
    ('Whole home', 'under_furn', 'Under furniture (accessible)'),
    ('Whole home', 'upholstery', 'Vacuum upholstery / couches'),
    ('Floors', 'vacuum', 'Vacuum carpets & rugs'),
    ('Floors', 'mop', 'Mop hard floors'),
    ('Floors', 'stairs', 'Stairs'),
    ('Rooms', 'beds', 'Make beds'),
    ('Rooms', 'linens', 'Change linens'),
    ('Rooms', 'closets', 'Inside closets / shelves'),
    ('Rooms', 'trash', 'Empty trash'),
    ('Rooms', 'tidy', 'General tidy / straighten'),
    ('Other', 'laundry', 'Laundry'),
    ('Other', 'basement', 'Basement'),
    ('Other', 'garage', 'Garage'),
    ('Other', 'organize', 'Organizing'),
    ('Other', 'pets', 'Pet hair / pet surcharge'),
    ('Other', 'extra_time', 'Extra time beyond estimate'),
    ('Limits', 'move_furn', 'Move heavy furniture'),
    ('Limits', 'ladder', 'High areas / tall ladders'),
    ('Limits', 'biohazard', 'Biohazards, pet waste, mold, infestations'),
    ('Limits', 'haul_trash', 'Haul away large amounts of trash'),
    ('Limits', 'bulbs', 'Wet-wipe light bulbs'),
]
TASK_IDS = [t[1] for t in TASKS]

# Company metadata: pricing evidence, how deep/move relate to standard, sources
CO = {
    'Scrub Lou': dict(priced='instant form (live observation)', structure='three separate tiers on one checklist',
                      url='https://scrublou.com/checklist/ ; https://scrublou.com/terms-of-service/', raw='raw/scrub-lou_checklist.txt; raw/scrub-lou_terms_excerpts.txt', method='browser, verbatim'),
    'Maids in Apron': dict(priced='instant form (live observation)', structure='one room list; deep/move not itemised',
                           url='https://maidsinapron.com/residential-cleaning/ ; https://maidsinapron.com/move-in-cleaning-services-louisville/', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
    'Super Cleaning Service Louisville': dict(priced='Launch27 feed + 12 live checks', structure='deep = standard + list; move = standard + deep + list',
                                              url='https://supercleaningservicelouisville.com/services/', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
    'Red Feather Cleaning': dict(priced='instant form (live observation)', structure='separate standard / deep / move pages',
                                 url='https://redfeathercleaning.com/standard-cleaning-services/ ; /deep-cleaning-services/ ; /move-out-cleaning-service/', raw='raw/red-feather_standard_deep.txt; raw/webfetch_extractions.txt', method='browser verbatim (standard, deep); WebFetch (move)'),
    'Maid 2 Clean KY': dict(priced='Launch27 feed + 9 live checks (14 Oct)', structure='one standard checklist; deep and move are add-ons',
                            url='https://www.maid2cleanky.com/services/ ; https://www.maid2cleanky.com/terms-of-service/', raw='raw/maid-2-clean_checklist_terms.txt', method='browser, verbatim'),
    'Rocking Robins (R&R) Maids': dict(priced='reconstructed calculator formula', structure='basic list; deep/move add items',
                                       url='https://rrmaids.com/ (basic, deep, move pages) ; https://rrmaids.com/faqs/', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
    'Your Cleaning Krew': dict(priced='published hourly rates', structure='separate recurring / deep / move-out checklists',
                               url='https://yourcleaningkrew.com/cleaning-checklists/ (recurring, deep, move-out)', raw='raw/your-cleaning-krew_checklists.txt', method='browser, verbatim'),
    'Stitch Cleaning': dict(priced='published price list', structure='separate regular / deep / move pages',
                            url='https://stitchcleaning.com/regular-cleaning/ ; /deep-cleaning/ ; /move-in-and-move-out-cleaning/', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
    'Hello Cleaners': dict(priced='published "from" prices', structure='Louisville page (standard) + checklist page (deep, move-in, move-out)',
                           url='https://hellocleaners.us/locations/kentucky/louisville/ ; https://hellocleaners.us/checklist', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
    'LouBelle Cleaning': dict(priced='published hourly rate', structure='standard (upkeep) vs deluxe; full checklist on request',
                              url='https://www.loubellecleaning.com/services ; https://www.loubellecleaning.com/faq', raw='raw/webfetch_extractions.txt', method='browser, verbatim'),
    'MaidPro (Greater Louisville)': dict(priced='none (contact-gated)', structure='one 49-point checklist; add-ons by request',
                                         url='https://www.maidpro.com/checklist ; https://www.maidpro.com/louisville-ky/additional-services2', raw='raw/maidpro_checklist_form.txt', method='browser, verbatim'),
    'Merry Maids (Louisville)': dict(priced='none (contact-gated)', structure='national recurring / deep / move pages',
                                     url='https://merrymaids.com/cleaning-services/home ; /deep-clean ; /move-in-and-move-out ; /frequently-asked-questions', raw='raw/merry-maids_services_form.txt', method='browser, verbatim'),
    'The Maids (Southern Louisville)': dict(priced='none (contact-gated)', structure='national 22-step process; deep/move not itemised',
                                            url='https://www.maids.com/our-company/22-step-cleaning-process/ ; https://www.maids.com/services/moving-cleaning-services/', raw='raw/the-maids_process_form.txt', method='browser, verbatim'),
    'The Cleaning Authority (Louisville)': dict(priced='none (contact-gated)', structure='normal clean + rotating detail-clean zones; first two visits are deep cleans',
                                                url='https://www.thecleaningauthority.com/why-hire-us-/detail-clean-rotation-system-/ ; /our-cleaning-services/house-cleaning/', raw='raw/the-cleaning-authority_checklist_form.txt', method='browser, verbatim'),
    'Maid in the Ville': dict(priced='none (contact-gated)', structure='short service descriptions only',
                              url='https://www.maidintheville.com/residential-cleaning ; /deep-cleaning ; /move-out-cleaning', raw='raw/maid-in-the-ville_services_form.txt', method='browser, verbatim'),
    'Busy Brooms': dict(priced='published ranges (may be market ranges)', structure='no task list published',
                        url='https://busybroomsky.com/residential-cleaning/', raw='raw/webfetch_extractions.txt', method='browser'),
    'Cleanoria (Thumbtack)': dict(priced='published starting price', structure='no task list published',
                                  url='https://www.thumbtack.com/ky/louisville/house-cleaning/cleanoria-house-cleaning-louisville/service/569098244546895875', raw='raw/webfetch_extractions.txt', method='WebFetch summary'),
}

# (std, deep, move, supporting text). '' tier = NS. Use helper strings.
A = 'INC', 'INC', 'INC'
D = {}

D['Scrub Lou'] = {
    'counters': (*A, 'Clean countertops & backsplash'), 'k_sink': (*A, 'Clean & dry sink & soap dish'),
    'stovetop': (*A, 'Clean stovetop, burners, & control panels'), 'appl_ext': (*A, 'Clean exteriors of large appliances (fridge, oven, dishwasher)'),
    'micro_in': (*A, 'Clean microwave (inside & outside)'), 'cab_fronts': ('COND', 'INC', 'INC', 'Routine: "Spot clean cabinets & clean all handles"; deep/move: "Wipe down exteriors of all cabinets and drawers"'),
    'hood': ('EXC', 'INC', 'INC', '"Clean oven hood vent" – marked – for routine'),
    'cab_in': ('EXC', 'EXC', 'INC', '"Wipe down insides of cabinets & drawers" – move-in/out only'),
    'fridge_in': ('PAID', 'PAID', 'NS', 'Booking form extra: inside fridge $45'), 'oven_in': ('PAID', 'PAID', 'NS', 'Booking form extra: inside oven $45'),
    'toilet': (*A, 'Clean inside, outside & around toilet'), 'tub_shower': (*A, 'Clean & dry shower/tub'),
    'b_sink': (*A, 'Clean & dry sink, countertops, & soap dish; Polish towel racks'), 'mirrors': (*A, 'Clean all mirrors & glass'),
    'grout': ('EXC', 'INC', 'INC', '"Scrub tile grout in shower" – marked – for routine'),
    'dust': (*A, 'Dust furniture, lamps & lampshades; Dry dust decor and picture frames'), 'fans': (*A, 'Dust ceiling fans'),
    'fixtures': (*A, 'Dust light fixtures'), 'cobwebs': (*A, 'Remove cobwebs'),
    'bb_wipe': ('EXC', 'INC', 'INC', '"Wipe down baseboards" – marked – for routine'),
    'sills': ('INC', 'INC', 'INC', 'Routine: "Dust all windowsills, window frames, & ledges"; deep adds "Wipe down windowsills and window frames"'),
    'blinds': ('COND', 'COND', 'COND', 'Terms: "we do not clean/perform ... blinds that are prone to breaking" (other blinds not stated)'),
    'doors': ('EXC', 'INC', 'INC', '"Wipe down all doors & door frames" – marked – for routine'),
    'switches': (*A, 'Clean all light switches & doorknobs'),
    'win_in': ('PAID', 'PAID', 'NS', 'Booking form: interior windows $4/window glass only, $8 with tracks'),
    'vacuum': (*A, 'Vacuum / sweep / mop floors'), 'mop': (*A, 'Vacuum / sweep / mop floors'),
    'beds': ('COND', 'COND', 'NS', 'Make bed(s) & change sheets (if left out on edge of bed); N/A for move'),
    'linens': ('COND', 'COND', 'NS', 'change sheets (if left out on edge of bed)'),
    'closets': ('EXC', 'EXC', 'INC', '"Clean inside closets & wipe down shelves" – move only; deep includes inside linen closet in bathrooms'),
    'trash': (*A, 'Empty garbage and replace the bag'), 'tidy': ('INC', 'INC', 'INC', 'Tidy area(s), fold blankets, arrange pillows, etc.'),
    'upholstery': ('EXC', 'EXC', 'EXC', 'Terms: "We do not offer ... upholstery cleaning" (cleaning, not vacuuming)'),
    'basement': ('PAID', 'PAID', 'PAID', 'Booking form lists Basement as an extra (price varies)'),
    'under_furn': ('COND', 'COND', 'COND', 'Terms: behind/under appliances or furniture only if customer moves them first'),
    'extra_time': ('COND', 'COND', 'COND', 'Terms: price may change if job exceeds allotted time; pay for extra time or set priorities'),
    'move_furn': ('EXC', 'EXC', 'EXC', 'Terms: "do not use tall ladders ... or move any heavy furniture"'),
    'ladder': ('EXC', 'EXC', 'EXC', 'Terms: "no more than 3-step ladders"'),
    'biohazard': ('EXC', 'EXC', 'EXC', 'Terms: no hoarder homes, biohazards, infestations, black mold'),
    'haul_trash': ('EXC', 'EXC', 'EXC', 'Terms: no "large-scale trash disposal"'),
    'bulbs': ('EXC', 'EXC', 'EXC', 'Terms: "We do not offer wet wiping of light bulbs"'),
}

D['Maids in Apron'] = {  # one list; applied to standard only. Deep/move not itemised.
    'counters': ('INC', 'NS', 'NS', 'Clean countertops and backsplash'), 'k_sink': ('INC', 'NS', 'NS', 'Clean sinks'),
    'stovetop': ('INC', 'NS', 'NS', 'Detail the stovetop'), 'appl_ext': ('INC', 'NS', 'INC', 'Detail outside appliances; move-in page: "Cleaning all kitchen appliances"'),
    'micro_in': ('INC', 'NS', 'NS', 'Clean the microwave inside and out'), 'cab_fronts': ('INC', 'NS', 'NS', 'Clean exterior cabinets'),
    'cab_in': ('PAID', 'PAID', 'NS', 'Extras list: inside cabinets ($5/unit on booking form)'),
    'fridge_in': ('PAID', 'PAID', 'NS', 'Extras: interior fridge ($45 booking form)'), 'oven_in': ('PAID', 'PAID', 'NS', 'Extras: interior oven ($45 booking form)'),
    'dishes': ('PAID', 'PAID', 'NS', 'Booking form extra: dishes $65'),
    'toilet': ('INC', 'NS', 'INC', '"Detail the Porcelain Throne"; move-in: scrubbing toilets'), 'tub_shower': ('INC', 'NS', 'INC', 'Scrub showers and tubs'),
    'b_sink': ('INC', 'NS', 'INC', 'Clean sinks and vanities; polish fixtures'), 'mirrors': ('INC', 'NS', 'NS', 'Shine mirrors'),
    'dust': ('INC', 'NS', 'INC', 'Dust all surfaces; move-in: "Dusting everywhere, including the high-to-reach places"'),
    'fans': ('INC', 'NS', 'NS', 'Detail ceiling fans'), 'cobwebs': ('INC', 'NS', 'NS', 'Remove cobwebs'),
    'bb_wipe': ('INC', 'NS', 'INC', 'Wipe baseboards; move-in: cleaning baseboards'), 'blinds': ('INC', 'NS', 'NS', 'Dust and clean blinds; wet-wipe blinds is a paid extra ($5/unit)'),
    'doors': ('INC', 'NS', 'NS', 'Clean doors and frames'), 'switches': ('INC', 'NS', 'NS', 'Clean outlets and switches; sanitize high-touch areas'),
    'win_in': ('PAID', 'PAID', 'NS', 'Extras: interior window cleaning ($5/window booking form)'), 'vents': ('INC', 'NS', 'NS', 'Clean vents'),
    'vacuum': ('INC', 'NS', 'INC', 'Vacuum carpets, stairs, and rugs'), 'mop': ('INC', 'NS', 'INC', 'Vacuum and mop floors'), 'stairs': ('INC', 'NS', 'NS', 'Vacuum ... stairs'),
    'trash': ('INC', 'NS', 'NS', 'Empty trash'), 'laundry': ('PAID', 'PAID', 'NS', '"Laundry & Folding (one load only)" – $65 booking form'),
    'basement': ('PAID', 'PAID', 'NS', 'Extras: deep basement cleaning (finished basement $120 booking form)'),
    'organize': ('PAID', 'PAID', 'NS', 'Booking form extra: house organization $375'), 'pets': ('PAID', 'PAID', 'NS', 'Booking form: pets $10'),
}

S = 'Standard checklist'
D['Super Cleaning Service Louisville'] = {
    'counters': (*A, f'{S}: countertops; backsplash'), 'k_sink': (*A, f'{S}: sinks'), 'stovetop': (*A, f'{S}: stovetop & fan'),
    'appl_ext': (*A, f'{S}: dishwasher (outside only); oven (outside only); outside of fridge; small appliances; polish stainless'),
    'micro_in': ('NS', 'NS', 'NS', f'{S} lists "microwave" without saying inside or outside'),
    'cab_fronts': ('COND', 'INC', 'INC', 'Standard: cabinets "dusted & spot checked"; deep: "outsides of cabinets" (hand wash)'),
    'hood': ('COND', 'COND', 'COND', 'Standard lists "stovetop & fan" (hood fan not explicit); deep: "kitchen grease removal"'),
    'cab_in': ('NS', 'NS', 'INC', 'Move: "inside empty cabinets"'),
    'fridge_in': ('PAID', 'PAID', 'PAID', 'Upgrade: inside fridge & freezer +$65'), 'oven_in': ('PAID', 'PAID', 'PAID', 'Upgrade: inside oven +$65'),
    'toilet': (*A, f'{S}: toilet'), 'tub_shower': (*A, f'{S}: shower stall; bathtub; shower racks (as able)'),
    'b_sink': (*A, f'{S}: sinks; counters; faucets polished'), 'mirrors': (*A, f'{S}: mirrors; glass'),
    'soap_scum': ('INC', 'INC', 'INC', 'Standard: "remove soap scum"; deep: "full soap scum removal"'),
    'dust': (*A, f'{S}: dust top to bottom; furniture/decor'), 'fans': (*A, f'{S}: light fixtures/fans'), 'fixtures': (*A, f'{S}: light fixtures/fans'),
    'bb_dust': (*A, f'{S}: baseboards dusted'), 'bb_wipe': ('NS', 'INC', 'INC', 'Deep: "hand wash baseboards"'),
    'sills': (*A, f'{S}: blinds/sills'), 'blinds': (*A, f'{S}: blinds/sills'), 'doors': ('NS', 'INC', 'INC', 'Deep: "wood trim"'),
    'switches': ('INC', 'INC', 'INC', f'{S}: fingerprints (switch plates not named)'),
    'win_in': ('PAID', 'PAID', 'PAID', 'Upgrade: interior windows +$8 per window'),
    'upholstery': ('PAID', 'PAID', 'PAID', 'Upgrade: vacuum sectional +$15, small couch +$10'),
    'vacuum': (*A, f'{S}: vacuum floors; throw rugs'), 'mop': (*A, f'{S}: mop'), 'stairs': (*A, f'{S}: vacuum stairs'),
    'beds': (*A, f'{S}: make beds'), 'linens': ('PAID', 'PAID', 'PAID', 'Upgrade: linens +$10'),
    'trash': (*A, f'{S}: empty trash'), 'tidy': (*A, f'{S}: straighten; towels folded/hung'),
    'extra_time': ('PAID', 'PAID', 'PAID', 'Booking form: Additional Time $32.50 per 30 minutes'),
    'move_furn': ('EXC', 'EXC', 'EXC', 'FAQ: "We do not move large furniture"'), 'ladder': ('EXC', 'EXC', 'EXC', 'FAQ: "we do not clean from heights"'),
    'biohazard': ('EXC', 'EXC', 'EXC', 'FAQ: no biohazards'), 'haul_trash': ('EXC', 'EXC', 'EXC', 'FAQ: no "large amounts of trash"'),
}

RS, RD = 'Standard page', 'Deep page'
D['Red Feather Cleaning'] = {
    'counters': ('INC', 'INC', 'NS', f'{RS}: Cleaning and sanitizing countertops, sinks, and stovetops; {RD}: Full sanitization of countertops, sinks, and backsplash'),
    'k_sink': ('INC', 'INC', 'NS', f'{RS}: countertops, sinks, and stovetops'), 'stovetop': ('INC', 'NS', 'NS', f'{RS}: countertops, sinks, and stovetops'),
    'appl_ext': ('INC', 'INC', 'NS', f'{RS}: Wiping down exterior surfaces of appliances; {RD}: interior and exterior of appliances; polishing metal appliances'),
    'micro_in': ('INC', 'NS', 'INC', f'{RS}: Cleaning the inside of microwaves; move: microwaves'),
    'fridge_in': ('PAID', 'INC', 'INC', f'{RD}: "cleaning the interior and exterior of appliances"; move: refrigerators; add-on "+$50–$100" (inside appliances)'),
    'oven_in': ('PAID', 'INC', 'INC', f'{RD}: interior of appliances; move: ovens; add-on "+$50–$100"'),
    'hood': ('NS', 'INC', 'NS', f'{RD}: Degreasing of stove hoods'), 'cab_in': ('NS', 'NS', 'INC', 'Move: inside cabinets/drawers (WebFetch)'),
    'cab_fronts': ('NS', 'NS', 'NS', 'Not itemised'),
    'toilet': ('INC', 'INC', 'NS', f'{RS}: Scrubbing and sanitizing sinks, countertops, toilets, showers, and tubs'),
    'tub_shower': ('INC', 'INC', 'NS', f'{RS}: showers, and tubs'), 'b_sink': ('INC', 'INC', 'NS', f'{RS}: sinks, countertops'),
    'mirrors': ('INC', 'INC', 'NS', f'{RS}: Cleaning mirrors and glass surfaces'), 'grout': ('NS', 'NS', 'INC', 'Move: "tile grout & walls" (WebFetch)'),
    'dust': ('INC', 'INC', 'NS', f'{RS}: Dusting all surfaces, including furniture, shelves'), 'fixtures': ('INC', 'INC', 'NS', f'{RS}: Dusting furniture, light fixtures (dining); {RD}: fixtures'),
    'fans': ('NS', 'INC', 'NS', f'{RD}: Ceiling fans dusted and cleaned'), 'cobwebs': ('INC', 'INC', 'NS', f'{RS}: Removing cobwebs from ceilings and corners'),
    'bb_dust': ('INC', 'INC', 'NS', f'{RS}: Dusting all surfaces, including ... baseboards'), 'bb_wipe': ('NS', 'INC', 'NS', f'{RD}: Baseboards cleaned to remove scuffs and grime; bathrooms: Baseboards scrubbed'),
    'sills': ('INC', 'NS', 'NS', f'{RS}: Light dusting of window sills and blinds'), 'blinds': ('INC', 'INC', 'NS', f'{RS}: Light dusting of ... blinds; {RD}: Window blinds cleaned'),
    'switches': ('NS', 'NS', 'INC', 'Move: light switches (WebFetch)'), 'walls': ('NS', 'NS', 'INC', 'Move: "tile grout & walls" (WebFetch)'),
    'closets': ('NS', 'NS', 'INC', 'Move: closets/drawers check (WebFetch)'),
    'win_in': ('PAID', 'PAID', 'PAID', 'Add-on "+$50–$100": interior windows'),
    'vacuum': ('INC', 'INC', 'NS', f'{RS}: Vacuuming or sweeping and mopping floors'), 'mop': ('INC', 'INC', 'NS', f'{RS}: Vacuuming or sweeping and mopping floors'),
    'beds': ('INC', 'COND', 'NS', f'{RS}: Making beds and organizing bedding; {RD}: Making beds (if applicable)'),
    'trash': ('INC', 'NS', 'NS', f'{RS}: Emptying trash'), 'tidy': ('INC', 'NS', 'NS', f'{RS}: organizing countertops; organizing bedding'),
    'laundry': ('COND', 'COND', 'NS', f'{RS}: Laundry room – exterior of washer/dryer wiped (no laundry service stated)'),
    'extra_time': ('PAID', 'PAID', 'PAID', 'Add-on "+$50–$100": heavy soil'),
}

M2 = 'Checklist'
D['Maid 2 Clean KY'] = {  # deep & move are add-ons to the standard checklist
    'counters': (*A, f'{M2}: Clean Counter Tops; Clean Backsplash'), 'k_sink': (*A, f'{M2}: Kitchen Sink'), 'stovetop': (*A, f'{M2}: Clean Stove Tops'),
    'appl_ext': (*A, f'{M2}: Wipe Down Exterior of Appliances'), 'micro_in': ('NS', 'NS', 'NS', f'{M2}: "Clean Microwave" (inside/outside not stated)'),
    'cab_fronts': ('COND', 'COND', 'COND', 'Clean Cabinet Fronts (As Needed)'), 'hood': (*A, f'{M2}: Wipe Down Hood range'),
    'cab_in': ('PAID', 'PAID', 'INC', 'Extra: Inside Cabinets $20 ("remove all items"); move includes Interior Cabinets/Drawers/Pantries'),
    'fridge_in': ('PAID', 'PAID', 'INC', 'Extra: Inside the Fridge $25 ("empty the fridge prior"); move includes Interior Fridge/Freezer'),
    'oven_in': ('PAID', 'PAID', 'INC', 'Extra: Inside the Oven $25; move includes Interior Oven'),
    'dishes': ('COND', 'COND', 'COND', 'Load Dishwasher (If available); "SERVICES NOT OFFERED: Putting Away Dishes"'),
    'toilet': (*A, f'{M2}: Clean Toilet'), 'tub_shower': (*A, f'{M2}: Clean Shower/Tub'), 'b_sink': (*A, f'{M2}: Clean Sinks; Clean Countertops'),
    'mirrors': (*A, f'{M2}: Clean Mirrors'), 'dust': (*A, f'{M2}: Dusting All Surfaces'), 'fans': (*A, f'{M2}: Wipe Fan Blades'),
    'fixtures': (*A, f'{M2}: Dust Lamps/Light Fixtures'), 'cobwebs': ('COND', 'COND', 'COND', 'Cobweb Removal (As needed)'),
    'bb_wipe': ('PAID', 'PAID', 'PAID', 'Extra: Wet Wipe Baseboards (per floor) $20'),
    'sills': (*A, f'{M2}: Dust Windowsills/Ledges'), 'blinds': ('PAID', 'PAID', 'PAID', 'Extra: Wet Wiping Blinds (per set) $5'),
    'doors': ('COND', 'COND', 'COND', 'Clean Doors (As Needed)'), 'switches': ('COND', 'COND', 'COND', 'Wipe Door Handles; Wipe Light Switches (As needed)'),
    'win_in': ('PAID', 'PAID', 'PAID', 'Extra: Inside Windows (Reachable) $60'), 'win_out': ('EXC', 'EXC', 'EXC', 'Services not offered: Cleaning Window Exteriors'),
    'walls': ('PAID', 'PAID', 'PAID', 'Extra: Spot Clean Walls $25'),
    'vacuum': (*A, f'{M2}: Vacuum Carpet'), 'mop': (*A, f'{M2}: Mop/Swifter The Floor'), 'stairs': (*A, f'{M2}: Clean Hallways and Stairs'),
    'beds': (*A, f'{M2}: Make The Bed'), 'linens': ('COND', 'COND', 'COND', 'Replace Bed Sheets (If provided)'),
    'closets': ('NS', 'NS', 'INC', 'Move: Clean Inside Linen Closet & Shelves'),
    'trash': (*A, f'{M2}: Empty Trash; Replace Trash Bags'), 'tidy': (*A, f'{M2}: General Tidying Up; Return Items To Original Locations'),
    'laundry': ('PAID', 'PAID', 'PAID', 'Extra: Load of Laundry $20'), 'basement': ('PAID', 'PAID', 'PAID', 'Extra: Finished Basement $50'),
    'garage': ('PAID', 'PAID', 'PAID', 'Extra: Garage $25'), 'organize': ('PAID', 'PAID', 'PAID', 'Extra: One Hr of Organizing $60'),
    'pets': ('PAID', 'PAID', 'PAID', 'Extra: Pet Hair $20'),
    'extra_time': ('COND', 'COND', 'COND', 'Deep/move: "if home is in poor condition the fee will be changed from flat rate to hourly"; terms: may reschedule extra time'),
    'move_furn': ('EXC', 'EXC', 'EXC', 'Services not offered: Moving Furniture'), 'ladder': ('EXC', 'EXC', 'EXC', 'Not offered: Anything That Requires A High Ladder'),
    'haul_trash': ('EXC', 'EXC', 'EXC', 'Not offered: Hauling Trash Away'), 'bulbs': ('EXC', 'EXC', 'EXC', 'Not offered: Wet Wiping Light Bulbs'),
}

RR = 'Basic list'
D['Rocking Robins (R&R) Maids'] = {
    'counters': (*A, f'{RR}: counters'), 'k_sink': (*A, f'{RR}: sinks'), 'stovetop': (*A, f'{RR}: stovetop/drip pans'),
    'appl_ext': (*A, f'{RR}: outside appliances; top of fridge'), 'micro_in': ('NS', 'INC', 'INC', 'Deep/move add: inside microwave'),
    'cab_fronts': ('NS', 'INC', 'INC', 'Deep/move add: cabinet fronts'), 'cab_in': ('NS', 'NS', 'INC', 'Vacant homes: inside cabinets/drawers'),
    'fridge_in': ('PAID', 'PAID', 'PAID', 'Paid extra: inside fridge / freezer ($60 each, 13 Oct calculator)'),
    'dishes': ('EXC', 'EXC', 'EXC', 'dishes not included'),
    'toilet': ('NS', 'NS', 'NS', 'Basic list names tub/shower, sinks, fixtures; toilet not itemised in extraction'),
    'tub_shower': ('INC', 'INC', 'INC', 'Basic: tub/shower; deep/move: double-scrubbed tub'), 'b_sink': (*A, f'{RR}: sinks; fixtures'), 'mirrors': (*A, f'{RR}: mirrors'),
    'dust': (*A, f'{RR}: lamps; pictures; furniture polished; moldings'), 'fans': ('INC', 'INC', 'INC', f'{RR}: dusting fans/fixtures; FAQ: deep from a two-step ladder; not unreachable/vaulted fans'),
    'fixtures': ('COND', 'COND', 'COND', 'Dusting fixtures; "reachable light fixtures"; unreachable chandeliers skipped'),
    'cobwebs': (*A, f'{RR}: cobwebs'), 'bb_dust': (*A, f'{RR}: baseboards dusted'), 'bb_wipe': ('NS', 'INC', 'INC', 'Deep/move add: hand washing (baseboards per FAQ)'),
    'blinds': ('PAID', 'PAID', 'PAID', 'Calculator extra: blinds $20 each'), 'doors': ('NS', 'INC', 'INC', 'Deep/move add: doors/frames'),
    'switches': ('NS', 'INC', 'INC', 'Deep/move add: switch plates'), 'win_in': ('PAID', 'PAID', 'PAID', 'Paid extra: interior windows ($5 each)'),
    'vacuum': (*A, f'{RR}: floors'), 'mop': (*A, f'{RR}: floors'), 'stairs': (*A, f'{RR}: stairs'), 'trash': (*A, f'{RR}: wastebaskets'),
    'closets': ('EXC', 'EXC', 'INC', 'No closets/utility/laundry/unfinished areas unless move'),
    'laundry': ('EXC', 'EXC', 'COND', 'No laundry areas unless move'), 'basement': ('COND', 'COND', 'COND', 'No unfinished areas unless move; calculator prices basements'),
    'move_furn': ('EXC', 'EXC', 'EXC', "can't move furniture"), 'ladder': ('EXC', 'EXC', 'EXC', 'no higher than 2-step ladder'),
}

YR, YD, YM = 'Recurring list', 'Deep list', 'Move-out list'
D['Your Cleaning Krew'] = {
    'counters': (*A, 'Clean counters and backsplash (all three lists)'), 'k_sink': (*A, 'Clean and dry sinks and countertops; move: remove hard water stains'),
    'stovetop': (*A, 'Clean stovetop, burners, front, and control panels'), 'appl_ext': ('INC', 'INC', 'NS', 'Clean and wipe exterior of appliances (recurring, deep)'),
    'micro_in': (*A, 'Clean inside and outside of microwave'), 'cab_fronts': (*A, 'Clean front of all cabinets and handles'),
    'hood': ('NS', 'INC', 'NS', f'{YD}: Clean oven hood vent'),
    'cab_in': ('PAID', 'PAID', 'INC', 'Add-on: Inside cabinets; move-out: Clean inside all cabinets and drawers'),
    'fridge_in': ('PAID', 'INC', 'INC', f'Recurring add-on: Inside fridge; {YD}: Clean inside the refrigerator and oven; move: inside/outside fridge & freezer'),
    'oven_in': ('PAID', 'INC', 'INC', f'Recurring add-on: Inside oven; {YD}: inside oven; move: Clean inside oven'),
    'dishes': ('COND', 'COND', 'NS', 'Gather dishes and glassware; add-ons: Load Dishwasher, Hand Wash Dishes'),
    'toilet': (*A, 'Clean and sanitize toilets / Scrub toilet inside and out'), 'tub_shower': (*A, 'Clean and scrub tubs and showers (including faucets, doors, tracks, and glass)'),
    'b_sink': (*A, 'Clean and dry sinks, counters, and soap dishes; polish towel racks'), 'mirrors': (*A, 'Clean mirrors and glass'),
    'grout': ('NS', 'INC', 'INC', f'{YD}: Scrub tile grout; {YM}: Scrub grout and tile thoroughly'),
    'soap_scum': ('NS', 'NS', 'INC', f'{YM}: remove soap scum; remove hard water stains'),
    'dust': ('INC', 'INC', 'NS', 'Dust furniture, lamps, and lampshades'), 'fans': ('COND', 'COND', 'INC', 'Dust ceiling fans and blades (from reasonable height)'),
    'fixtures': (*A, 'Dust light fixtures'), 'cobwebs': ('COND', 'COND', 'NS', 'Clean cobwebs ... (from reasonable height)'),
    'bb_wipe': ('NS', 'INC', 'INC', f'{YD}: Clean baseboards; {YM}: Wipe down baseboards throughout property'),
    'sills': (*A, 'Clean window sills, frames, and chair rails'), 'blinds': ('NS', 'INC', 'INC', f'{YD}: Wet wipe blinds and shutters; {YM}: Dust blinds or wipe shutters'),
    'doors': ('NS', 'INC', 'INC', 'Wipe down doors and door frames (deep, move)'), 'switches': ('NS', 'INC', 'INC', 'Clean light switches and door knobs (deep); switches and outlets (move)'),
    'win_in': ('PAID', 'PAID', 'NS', 'Add-on: Windows and tracks'), 'walls': ('NS', 'INC', 'COND', f'{YD}: Spot clean walls; {YM}: Spot clean walls where needed'),
    'vents': ('NS', 'NS', 'INC', f'{YM}: Clean air vents and returns'), 'under_furn': ('NS', 'INC', 'INC', f'{YD}: Clean under furniture; {YM}: Vacuum under where furniture was'),
    'vacuum': (*A, 'Vacuum carpets'), 'mop': (*A, 'Sweep, mop, and vacuum all floors'), 'stairs': ('INC', 'INC', 'NS', 'Clean hallways and staircases'),
    'beds': ('COND', 'COND', 'NS', 'Make beds and change sheets (if clean sheets are provided)'), 'linens': ('COND', 'COND', 'NS', 'change sheets (if clean sheets are provided)'),
    'closets': ('NS', 'NS', 'INC', f'{YM}: Clean inside all closets and shelving'), 'trash': ('INC', 'INC', 'NS', 'Empty bins and take out trash (2-3 bags max)'),
    'tidy': ('INC', 'INC', 'NS', 'Dust and tidy knick-knacks; Tidy areas, fold blankets'),
    'laundry': ('PAID', 'PAID', 'COND', 'Add-on: Load Laundry; move: laundry area/washer-dryer (if applicable)'),
    'basement': ('PAID', 'PAID', 'COND', 'Add-on: Basement Area; move: Clean basement (if applicable)'),
    'garage': ('NS', 'NS', 'COND', f'{YM}: Sweep garage/patio (if applicable)'),
    'haul_trash': ('COND', 'COND', 'NS', 'take out trash (2-3 bags max)'),
}

D['Stitch Cleaning'] = {
    'dust': ('INC', 'INC', 'INC', 'Regular: "Dusting and wiping down all surfaces"; move: dusting all surfaces'),
    'vacuum': ('INC', 'INC', 'INC', 'Sweeping, mopping, and vacuuming floors'), 'mop': ('INC', 'INC', 'INC', 'Sweeping, mopping, and vacuuming floors'),
    'tidy': ('INC', 'NS', 'NS', 'General tidying of living spaces and bedrooms'),
    'counters': ('NS', 'INC', 'INC', 'Deep: countertops; move: sanitizing countertops and backsplashes'), 'k_sink': ('NS', 'INC', 'NS', 'Deep: sinks'),
    'appl_ext': ('NS', 'INC', 'INC', 'Deep: appliances; move: appliance exteriors'), 'cab_fronts': ('NS', 'INC', 'INC', 'Deep: cabinets; move: wiping cabinet fronts'),
    'hood': ('NS', 'NS', 'INC', 'Move: degreasing stovetops, ovens, and range hoods'), 'stovetop': ('NS', 'NS', 'INC', 'Move: degreasing stovetops'),
    'fridge_in': ('NS', 'NS', 'COND', 'Move: interior appliance cleaning is "optional" / "upon request"'),
    'toilet': ('NS', 'INC', 'INC', 'Deep: toilets; move: scrubbing and disinfecting toilets'), 'tub_shower': ('NS', 'INC', 'INC', 'Deep: showers; move: showers, tiles'),
    'mirrors': ('NS', 'INC', 'INC', 'Deep/move: mirrors'), 'b_sink': ('NS', 'INC', 'INC', 'Deep: sinks; move: polishing chrome fixtures'),
    'fans': ('NS', 'INC', 'NS', 'Deep: ceiling fans'), 'fixtures': ('NS', 'INC', 'NS', 'Deep: light fixtures'),
    'blinds': ('NS', 'INC', 'NS', 'Deep: "Window washing, blind wiping, and track cleaning"'), 'win_in': ('NS', 'INC', 'NS', 'Deep: "Window washing"'),
    'under_furn': ('NS', 'INC', 'NS', 'Deep: spots "behind or under furniture"'), 'bb_wipe': ('NS', 'NS', 'INC', 'Move: wiping baseboards'),
    'sills': ('NS', 'NS', 'INC', 'Move: windowsills'), 'switches': ('NS', 'NS', 'INC', 'Move: light switches'),
    'biohazard': ('EXC', 'EXC', 'EXC', 'Move page exclusions: "Hazardous materials"; full list on request'),
    'extra_time': ('NS', 'NS', 'COND', 'Move: if home not empty "additional time may be needed"'),
}

D['Hello Cleaners'] = {
    'counters': ('INC', 'INC', 'NS', 'Standard: countertops; deep: deep-clean counters and backsplash'), 'k_sink': ('INC', 'NS', 'COND', 'Standard: sink and faucets cleaned and descaled'),
    'stovetop': ('INC', 'NS', 'NS', 'Standard: degreasing the stovetop'), 'appl_ext': ('INC', 'NS', 'NS', 'Standard: appliance exteriors'),
    'cab_fronts': ('INC', 'INC', 'INC', 'Standard: wiping cabinet fronts, handles; deep: cabinet fronts "inside and out"; move-out: cabinets inside and out'),
    'cab_in': ('NS', 'INC', 'INC', 'Deep: "Wipe cabinet fronts, inside and out"; move-in/out: inside cabinets and drawers'),
    'fridge_in': ('PAID', 'PAID', 'INC', 'Add-on: inside fridge; move-in: clean inside the refrigerator; move-out: inside and behind fridge'),
    'oven_in': ('PAID', 'PAID', 'INC', 'Add-on: inside oven; move-out: deep-clean and degrease the oven'),
    'toilet': ('INC', 'INC', 'INC', 'Standard: sanitizing the toilet'), 'tub_shower': ('INC', 'INC', 'INC', 'Standard: shower door, tiles; deep: descale showers, tubs'),
    'grout': ('INC', 'NS', 'INC', 'Standard: "shower door, tiles and grout"; move-out: scrub grout and remove mold'),
    'mirrors': ('INC', 'NS', 'NS', 'Standard: polishing mirrors, chrome'), 'b_sink': ('INC', 'INC', 'INC', 'Standard: sink; fittings'),
    'soap_scum': ('NS', 'INC', 'INC', 'Deep: descale; move-out: remove hard-water scale'),
    'dust': ('INC', 'INC', 'NS', 'Dusting from high surfaces down'), 'fans': ('NS', 'INC', 'NS', 'Deep: clean light fixtures and ceiling fans'),
    'fixtures': ('NS', 'INC', 'NS', 'Deep: clean light fixtures'), 'cobwebs': ('NS', 'INC', 'NS', 'Deep: remove cobwebs'),
    'bb_wipe': ('NS', 'INC', 'INC', 'Deep: hand-clean baseboards, trim; move-out: hand-clean baseboards'),
    'doors': ('INC', 'INC', 'NS', 'Standard: wiping ... door frames; deep: door frames'), 'switches': ('INC', 'INC', 'INC', 'Standard: wiping switches, handles'),
    'win_in': ('PAID', 'INC', 'INC', 'Add-on: interior windows; deep: clean interior windows and sills; move: interior windows and tracks'),
    'walls': ('PAID', 'PAID', 'INC', 'Add-on: wall spot-clean; move-out: spot-clean walls'), 'vents': ('NS', 'INC', 'INC', 'Deep: dust vents; move-in: dust vents'),
    'vacuum': ('INC', 'INC', 'INC', 'vacuuming floors'), 'mop': ('INC', 'INC', 'INC', 'washing hard floors / vacuum and mop'),
    'closets': ('NS', 'NS', 'INC', 'Move: wipe shelving and closets / clean inside closets'),
    'trash': ('NS', 'INC', 'INC', 'Deep: empty trash; move-out: remove all trash and debris'), 'laundry': ('PAID', 'PAID', 'NS', 'Add-on: laundry (wash, dry, and fold)'),
}

D['LouBelle Cleaning'] = {
    'oven_in': ('NS', 'INC', 'NS', 'Deluxe: Oven Cleaning'), 'cab_in': ('NS', 'INC', 'NS', 'Deluxe: Clean & Wash All Cabinetry (Inside & Out)'),
    'cab_fronts': ('NS', 'INC', 'NS', 'Deluxe: Clean & Wash All Cabinetry (Inside & Out)'), 'fridge_in': ('NS', 'INC', 'NS', 'Deluxe: Fridge & Freezer Cleaning'),
    'closets': ('NS', 'INC', 'NS', 'Deluxe: Clean & Organize Pantries/Closets'), 'switches': ('NS', 'INC', 'NS', 'Deluxe: Clean Switch Plates & Door Handles'),
    'fixtures': ('NS', 'INC', 'NS', 'Deluxe: Clean & Wash Light Fixtures'), 'vents': ('NS', 'INC', 'NS', 'Deluxe: Vacuum & Wash Floor Vents'),
    'win_in': ('NS', 'COND', 'NS', 'Deluxe: Clean & Wash Windows, Casings & Ledges (Must Be Accessible From The Inside)'),
    'sills': ('NS', 'INC', 'NS', 'Deluxe: Windows, Casings & Ledges'),
    'laundry': ('COND', 'COND', 'COND', 'FAQ: "we do not provide full laundry or ironing services" but will put a load in "while still in the home"'),
    'organize': ('COND', 'COND', 'COND', 'FAQ: happy to organize and pick up "at your request"; discuss at or before initial clean'),
}

MP = '49-Point Checklist'
D['MaidPro (Greater Louisville)'] = {  # one checklist; deep/move not itemised locally
    'counters': ('INC', 'NS', 'NS', 'Countertops and backsplash disinfected (all items removed and replaced)'), 'k_sink': ('INC', 'NS', 'NS', 'Sinks scrubbed and disinfected'),
    'appl_ext': ('INC', 'NS', 'NS', 'Appliance exteriors cleaned (interiors upon request)'), 'micro_in': ('INC', 'NS', 'NS', 'Microwave exterior/interior cleaned'),
    'cab_fronts': ('INC', 'NS', 'NS', 'Cabinet fronts cleaned'),
    'fridge_in': ('COND', 'NS', 'NS', 'Appliance "interiors upon request"; Fridge Cleaning add-on via local office (price not published)'),
    'oven_in': ('COND', 'NS', 'NS', 'Appliance "interiors upon request"; Oven Cleaning add-on via local office (price not published)'),
    'dishes': ('COND', 'NS', 'NS', 'Sinks scrubbed and disinfected (dishes upon request)'),
    'toilet': ('INC', 'NS', 'NS', 'Toilets disinfected inside and out'), 'tub_shower': ('INC', 'NS', 'NS', 'Tub and shower tiles scrubbed, disinfected and rinsed'),
    'b_sink': ('INC', 'NS', 'NS', 'Sinks scrubbed; Chrome fixtures cleaned and shined; Countertops disinfected'), 'mirrors': ('INC', 'NS', 'NS', 'Mirrors cleaned'),
    'dust': ('INC', 'NS', 'NS', 'Furniture dusted - top, front and underneath; Picture frames dusted; Lamps cleaned'),
    'fans': ('COND', 'NS', 'NS', 'Ceiling fans dusted (height restrictions apply)'), 'fixtures': ('INC', 'NS', 'NS', 'Lamps cleaned and lampshades dusted'),
    'bb_dust': ('INC', 'NS', 'NS', 'Baseboards dusted'), 'sills': ('INC', 'NS', 'NS', 'Windowsills cleaned'),
    'blinds': ('COND', 'NS', 'NS', 'Windowsills cleaned (blinds dusted upon request)'),
    'switches': ('INC', 'NS', 'NS', 'Fingerprints removed from all woodwork, doorframes and switch plates'),
    'doors': ('INC', 'NS', 'NS', 'Fingerprints removed from all woodwork, doorframes'),
    'under_furn': ('COND', 'NS', 'NS', 'Floors vacuumed and/or washed (under bed if accessible)'), 'upholstery': ('INC', 'NS', 'NS', 'Upholstered furniture vacuumed'),
    'vacuum': ('INC', 'NS', 'NS', 'Carpets vacuumed'), 'mop': ('INC', 'NS', 'NS', 'Hardwood/Tile floors vacuumed and/or washed'), 'stairs': ('INC', 'NS', 'NS', 'Hallways and stairs vacuumed and/or washed'),
    'beds': ('INC', 'NS', 'NS', 'Beds made'), 'linens': ('COND', 'NS', 'NS', 'Beds made (linens changed upon request)'),
    'trash': ('INC', 'NS', 'NS', 'Trash emptied'), 'tidy': ('INC', 'NS', 'NS', 'General straightening completed; Cushions and pillows fluffed'),
}

D['Merry Maids (Louisville)'] = {
    'counters': ('INC', 'NS', 'INC', 'Recurring: dusting and cleaning kitchen surfaces; move: sanitize all countertops, sinks, and backsplashes'),
    'k_sink': ('INC', 'INC', 'INC', 'Cleaning and polishing sinks; deep: scrub sinks; move: sinks'),
    'appl_ext': ('INC', 'NS', 'INC', 'Recurring: exterior of kitchen appliances (oven, stove, refrigerator, etc.); move: inside and outside appliances'),
    'fridge_in': ('NS', 'NS', 'INC', 'Move: "thoroughly clean the inside and outside your kitchen appliances"'), 'oven_in': ('NS', 'NS', 'INC', 'Move: inside and outside kitchen appliances'),
    'cab_fronts': ('INC', 'NS', 'INC', 'Recurring: wiping down furniture and cabinets; move: outside of your cabinets and drawers'),
    'cab_in': ('COND', 'COND', 'COND', 'FAQ special request: "cleaning inside cabinets"'),
    'toilet': ('INC', 'INC', 'INC', 'Polishing ... toilets; deep: clean toilets inside and out'), 'tub_shower': ('INC', 'INC', 'INC', 'showers, and tubs'),
    'b_sink': ('INC', 'INC', 'INC', 'sinks ... fixtures; move: vanities, polish fixtures'), 'mirrors': ('INC', 'INC', 'INC', 'Cleaning mirrors and glass surfaces'),
    'dust': ('INC', 'INC', 'INC', 'Dusting windowsills, surfaces, and knick-knacks'), 'sills': ('INC', 'NS', 'NS', 'Dusting windowsills'),
    'fans': ('NS', 'COND', 'INC', 'Deep: wet-wiping ceiling fans (where accessible); move: dust ceiling fans'), 'fixtures': ('NS', 'INC', 'INC', 'Deep: light fixtures; move: light fixtures'),
    'vents': ('NS', 'INC', 'NS', 'Deep: vents'), 'doors': ('NS', 'INC', 'NS', 'Deep: wet-wipe doors, door frames'), 'switches': ('NS', 'INC', 'NS', 'Deep: doorknobs, and light switch plates'),
    'bb_dust': ('NS', 'NS', 'INC', 'Move: dust ... baseboards; Baseboard Cleaning'), 'bb_wipe': ('COND', 'COND', 'INC', 'FAQ special request: de-griming baseboards; move: baseboard cleaning'),
    'walls': ('NS', 'NS', 'INC', 'Move: Wall Washing ... remove cobwebs, dirt and grime from your walls'), 'cobwebs': ('NS', 'NS', 'INC', 'Move: remove cobwebs'),
    'vacuum': ('INC', 'INC', 'INC', 'Vacuuming and mopping floors'), 'mop': ('INC', 'INC', 'INC', 'Vacuuming and mopping floors'),
    'trash': ('INC', 'NS', 'NS', 'Emptying trash and recycling bins'), 'pets': ('COND', 'COND', 'COND', 'FAQ special request: removing pet hair from furniture'),
    'closets': ('COND', 'COND', 'COND', 'FAQ special request: de-cluttering closets'),
}

TM = '22-Step process'
D['The Maids (Southern Louisville)'] = {
    'counters': ('INC', 'NS', 'NS', f'{TM}: Counters'), 'k_sink': ('INC', 'NS', 'NS', f'{TM}: Sink and hardware'), 'stovetop': ('INC', 'NS', 'NS', f'{TM}: Range top'),
    'appl_ext': ('INC', 'NS', 'NS', f'{TM}: Appliance exteriors'), 'micro_in': ('INC', 'NS', 'NS', f'{TM}: Inside microwave'), 'cab_fronts': ('INC', 'NS', 'NS', f'{TM}: Cabinet doors'),
    'dishes': ('INC', 'NS', 'NS', '"We\'ll even load the dishwasher!"'),
    'toilet': ('INC', 'NS', 'NS', 'Clean and disinfect the toilet, tub, and shower'), 'tub_shower': ('INC', 'NS', 'NS', 'Clean and disinfect the toilet, tub, and shower'),
    'b_sink': ('INC', 'NS', 'NS', 'Clean and disinfect sinks, hardware, counters, and even switch plates'), 'switches': ('INC', 'NS', 'NS', 'bathroom: even switch plates'),
    'dust': ('INC', 'NS', 'INC', 'Dust and vacuum furniture; move: Dusting surfaces throughout the home'), 'sills': ('INC', 'NS', 'NS', 'Dust sills, ledges, and wall hangings'),
    'cobwebs': ('INC', 'NS', 'NS', 'Remove cobwebs'), 'win_in': ('COND', 'NS', 'NS', 'Window over the kitchen sink; Clean entry window and one set of patio doors'),
    'upholstery': ('INC', 'NS', 'NS', 'Dust and vacuum furniture'), 'vacuum': ('INC', 'NS', 'NS', 'Vacuum floors, rugs, and carpet'), 'mop': ('INC', 'NS', 'NS', f'{TM}: Floors'),
    'stairs': ('INC', 'NS', 'NS', 'Vacuum stairs'), 'beds': ('INC', 'NS', 'NS', 'Make beds'), 'linens': ('COND', 'NS', 'NS', 'change out the towels (bath towels only stated)'),
    'trash': ('INC', 'NS', 'NS', 'Empty trash'), 'tidy': ('INC', 'NS', 'NS', 'Perform a quick pickup and straighten'),
    'bb_dust': ('NS', 'COND', 'NS', 'Deep/same-day page: "From baseboards to bathroom tile" (not itemised)'),
}

TC = 'Normal clean'
D['The Cleaning Authority (Louisville)'] = {  # deep = rotation detail-clean additions
    'counters': ('INC', 'INC', 'NS', f'{TC}: Counter tops cleaned and sanitized'), 'k_sink': ('INC', 'INC', 'NS', 'Sinks cleaned and sanitized and chrome shined'),
    'stovetop': ('INC', 'INC', 'NS', 'Top and front of range cleaned; Drip pans or glass top surfaces wiped'), 'appl_ext': ('INC', 'INC', 'NS', 'Fronts of all appliances cleaned; rotation: Appliances cleaned and shined'),
    'micro_in': ('INC', 'INC', 'NS', 'Microwave wiped out'), 'cab_fronts': ('NS', 'INC', 'NS', 'Rotation: Fronts of cabinets hand wiped'),
    'hood': ('INC', 'INC', 'NS', 'Outside of range hood cleaned; rotation: Inside of range hood cleaned'),
    'fridge_in': ('PAID', 'PAID', 'NS', 'Separate Refrigerator Cleaning service page (price not published)'), 'oven_in': ('PAID', 'PAID', 'NS', 'Separate Oven Cleaning service page (price not published)'),
    'toilet': ('INC', 'INC', 'NS', 'Toilets thoroughly cleaned'), 'tub_shower': ('INC', 'INC', 'NS', 'Tile walls, bathtubs, and showers cleaned and sanitized; Shower doors'),
    'b_sink': ('INC', 'INC', 'NS', 'Vanity and sink cleaned and sanitized; rotation: drains cleaned with a toothbrush'), 'mirrors': ('INC', 'INC', 'NS', 'Mirrors and chrome fixtures cleaned and shined'),
    'grout': ('NS', 'INC', 'NS', 'Rotation: Tile grouting scrubbed'),
    'dust': ('INC', 'INC', 'NS', 'Flat areas hand wiped and sanitized; Intricate items dusted; rotation: Furniture surfaces hand wiped'),
    'fans': ('INC', 'INC', 'NS', 'Ceiling fans dusted'), 'fixtures': ('INC', 'INC', 'NS', 'Lamp shades dusted'), 'cobwebs': ('INC', 'INC', 'NS', 'Cobwebs removed'),
    'bb_wipe': ('NS', 'INC', 'NS', 'Rotation: Baseboards hand wiped'), 'sills': ('INC', 'INC', 'NS', 'Window sills, ledges, and blinds dusted; rotation: hand wiped'),
    'blinds': ('INC', 'INC', 'NS', 'Window sills, ledges, and blinds dusted'), 'doors': ('COND', 'INC', 'NS', 'Doors and door frames spot cleaned; rotation: hand wiped'),
    'switches': ('INC', 'INC', 'NS', 'house-cleaning page: sanitizing high-touch surfaces like light switches, doorknobs'),
    'under_furn': ('NS', 'COND', 'NS', 'Rotation: Accessible areas under furniture vacuumed'), 'upholstery': ('NS', 'INC', 'NS', 'Rotation: Furniture and upholstery vacuumed'),
    'vacuum': ('INC', 'INC', 'NS', 'All readily accessible floors vacuumed'), 'mop': ('INC', 'INC', 'NS', 'Clean hard surfaced floors: vacuumed and damp mopped'),
    'stairs': ('INC', 'INC', 'NS', 'Stairs vacuumed'), 'closets': ('COND', 'COND', 'NS', 'Empty closet floors vacuumed (floors only)'),
    'basement': ('PAID', 'PAID', 'NS', 'Separate Basement Cleaning service page (price not published)'),
}

D['Maid in the Ville'] = {
    'dust': ('INC', 'INC', 'NS', 'Residential: Dusting; deep: dusting and cleaning all surfaces'), 'vacuum': ('INC', 'NS', 'NS', 'Vacuuming'),
    'beds': ('INC', 'NS', 'NS', 'Bed Making'), 'dishes': ('INC', 'NS', 'NS', 'Washing Dishes'), 'organize': ('INC', 'INC', 'NS', 'Residential: Organizing; deep: organizing closets and cabinets'),
    'toilet': ('INC', 'COND', 'NS', 'Bathroom Cleaning; deep: "can also include cleaning and disinfecting bathrooms"'),
    'under_furn': ('NS', 'INC', 'NS', 'Deep: Cleaning underneath furniture'), 'closets': ('NS', 'INC', 'NS', 'Deep: Cleaning and organizing closets and cabinets'),
    'cab_in': ('NS', 'INC', 'NS', 'Deep: Cleaning and organizing closets and cabinets'), 'fans': ('NS', 'INC', 'NS', 'Deep: Ceiling fans & light fixtures'),
    'fixtures': ('NS', 'INC', 'NS', 'Deep: Ceiling fans & light fixtures'), 'bb_wipe': ('NS', 'INC', 'NS', 'Residential page: deep addresses baseboards, cabinet fronts, appliances, and fixtures'),
    'cab_fronts': ('NS', 'INC', 'NS', 'deep: cabinet fronts'), 'appl_ext': ('NS', 'INC', 'NS', 'deep: appliances (inside/outside not stated)'),
}

D['Busy Brooms'] = {}
D['Cleanoria (Thumbtack)'] = {'win_in': ('PAID', 'PAID', 'PAID', 'Extras listed (no prices): interior window cleaning'),
                              'fridge_in': ('PAID', 'PAID', 'PAID', 'Extras: fridge cleaning'), 'oven_in': ('PAID', 'PAID', 'PAID', 'Extras: oven cleaning'),
                              'laundry': ('PAID', 'PAID', 'PAID', 'Extras: laundry'), 'pets': ('PAID', 'PAID', 'PAID', 'Extras: "houses with pets"')}

TIERS = ('standard', 'deep', 'move')
rows = []
for co, meta in CO.items():
    tasks = D[co]
    bad = set(tasks) - set(TASK_IDS)
    assert not bad, (co, bad)
    for area, tid, label in TASKS:
        st, dp, mv, txt = tasks.get(tid, ('NS', 'NS', 'NS', ''))
        rows.append(dict(company=co, area=area, task_id=tid, task=label, standard=st, deep=dp, move=mv,
                         supporting_text=txt, source_url=meta['url'], evidence_file=meta['raw'], capture_method=meta['method'],
                         captured=DATE, company_pricing_evidence=meta['priced'], company_tier_structure=meta['structure']))

with open(HERE / 'task_matrix_long.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# Wide view: one row per task, one column per company (standard / deep / move)
ABBR = {'INC': 'Inc', 'EXC': 'Excl', 'PAID': 'Paid', 'COND': 'Cond', 'NS': '–'}
cos = list(CO)
with open(HERE / 'task_matrix_wide.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['area', 'task'] + [f'{c} [std/deep/move]' for c in cos])
    for area, tid, label in TASKS:
        cells = []
        for c in cos:
            st, dp, mv, _ = D[c].get(tid, ('NS', 'NS', 'NS', ''))
            cells.append('/'.join(ABBR[x] for x in (st, dp, mv)))
        w.writerow([area, label] + cells)

# Summary: how many companies explicitly include each task in STANDARD, and how many sell it as an extra
PRICED = ['Scrub Lou', 'Maids in Apron', 'Super Cleaning Service Louisville', 'Red Feather Cleaning', 'Maid 2 Clean KY']
summ = []
for area, tid, label in TASKS:
    c = Counter(); cp = Counter(); paid_prices = []
    for co in cos:
        st = D[co].get(tid, ('NS',))[0]
        c[st] += 1
        if co in PRICED:
            cp[st] += 1
    for co in cos:
        st, dp, mv, txt = D[co].get(tid, ('NS', 'NS', 'NS', ''))
        if 'PAID' in (st, dp, mv) and '$' in txt:
            paid_prices.append(f'{co}: {txt}')
    summ.append(dict(area=area, task=label, std_included=c['INC'], std_conditional=c['COND'], std_paid_extra=c['PAID'], std_excluded=c['EXC'], std_not_stated=c['NS'],
                     priced5_std_included=cp['INC'], priced5_std_paid=cp['PAID'], priced5_std_excluded=cp['EXC'], priced5_std_conditional=cp['COND'], priced5_std_not_stated=cp['NS'],
                     published_extra_prices=' | '.join(paid_prices)))
with open(HERE / 'task_summary.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(summ[0].keys()))
    w.writeheader()
    w.writerows(summ)

print(len(rows), 'cells;', Counter(r['standard'] for r in rows))
for s in summ:
    print(f"{s['task'][:40]:40} std inc {s['std_included']:2} cond {s['std_conditional']:2} paid {s['std_paid_extra']:2} excl {s['std_excluded']:2} | priced5 inc {s['priced5_std_included']} paid {s['priced5_std_paid']} excl {s['priced5_std_excluded']}")
