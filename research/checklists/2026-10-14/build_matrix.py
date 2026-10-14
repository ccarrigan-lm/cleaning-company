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
                           url='https://maidsinapron.com/residential-cleaning/ ; /move-in-cleaning-services-louisville/ ; /terms-of-service/', raw='raw/maids-in-apron_checklist_terms.txt', method='browser, verbatim (re-read 14 Oct evening)'),
    'Super Cleaning Service Louisville': dict(priced='Launch27 feed + 12 live checks', structure='deep = standard + list; move = standard + deep + list',
                                              url='https://supercleaningservicelouisville.com/services/ ; /faq/', raw='raw/super-cleaning_checklist_faq.txt', method='browser, verbatim (re-read 14 Oct evening)'),
    'Red Feather Cleaning': dict(priced='instant form (live observation)', structure='separate standard / deep / move pages',
                                 url='https://redfeathercleaning.com/standard-cleaning-services/ ; /deep-cleaning-services/ ; /move-out-cleaning-service/', raw='raw/red-feather_standard_deep.txt; raw/red-feather_move-out_recapture.txt', method='browser, verbatim (standard, deep, move-out)'),
    'Maid 2 Clean KY': dict(priced='Launch27 feed + 9 live checks (14 Oct)', structure='one standard checklist; deep and move are add-ons',
                            url='https://www.maid2cleanky.com/services/ ; https://www.maid2cleanky.com/terms-of-service/', raw='raw/maid-2-clean_checklist_terms.txt', method='browser, verbatim'),
    'Rocking Robins (R&R) Maids': dict(priced='reconstructed calculator formula', structure='basic list; deep/move add items',
                                       url='https://rrmaids.com/basic-home-cleaning/ ; /top-to-bottom-deluxe-deep-cleaning/ ; /move-in-move-out-cleaning/ ; /faqs/', raw='raw/rr-maids_checklists_faq.txt', method='browser, verbatim (re-read 14 Oct evening)'),
    'Your Cleaning Krew': dict(priced='published hourly rates', structure='separate recurring / deep / move-out checklists',
                               url='https://yourcleaningkrew.com/cleaning-checklists/ (recurring, deep, move-out)', raw='raw/your-cleaning-krew_checklists.txt', method='browser, verbatim'),
    'Stitch Cleaning': dict(priced='published price list', structure='separate regular / deep / move pages; regular plans start with a deep clean', louisville='included: identity verified (KY SOS: active LLC, Jefferson County, principal office matches website)',
                            url='https://stitchcleaning.com/regular-cleaning/ ; /deep-cleaning/ ; /move-in-and-move-out-cleaning/ ; /louisville-cleaning-services-pricing/', raw='raw/stitch_checklists_pricing_identity.txt', method='browser, verbatim (re-read 14 Oct evening)'),
    'Hello Cleaners': dict(priced='published "from" prices', structure='national platform: Louisville page (standard) + national checklist (deep, move-in, move-out)', louisville='EXCLUDED from Louisville conclusions: national booking platform; no Louisville operator identified',
                           url='https://hellocleaners.us/locations/kentucky/louisville/ ; https://hellocleaners.us/checklist', raw='raw/hello-cleaners_louisville_checklist.txt', method='browser, verbatim (re-read 14 Oct evening)'),
    'LouBelle Cleaning': dict(priced='published hourly rate', structure='standard (upkeep) vs deluxe; full checklist on request',
                              url='https://www.loubellecleaning.com/services ; https://www.loubellecleaning.com/faq', raw='raw/loubelle_services_faq.txt', method='browser, verbatim'),
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
                        url='https://busybroomsky.com/residential-cleaning/', raw='raw/busy-brooms_residential.txt', method='browser'),
    'Cleanoria (Thumbtack)': dict(priced='published starting price', structure='no task list published',
                                  url='https://www.thumbtack.com/ky/louisville/house-cleaning/cleanoria-house-cleaning-louisville/service/569098244546895875', raw='raw/cleanoria_thumbtack.txt', method='browser, verbatim (re-read 14 Oct evening)'),
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

MA, MM = 'Residential list', 'Move-in list'
D['Maids in Apron'] = {  # one unlabeled residential list (sold as flat-rate house cleaning) -> coded as standard; deep is an add-on (terms: billed hourly)
    'counters': ('INC', 'NS', 'NS', f'{MA}: Clean Countertops; Clean Backsplash'), 'k_sink': ('INC', 'NS', 'INC', f'{MA}: Clean Sinks; {MM}: Cleaning the sinks'),
    'stovetop': ('INC', 'NS', 'NS', f'{MA}: Detail Stove Top'), 'appl_ext': ('INC', 'NS', 'INC', f'{MA}: Detail Outside Appliances; {MM}: Cleaning all kitchen appliances'),
    'micro_in': ('INC', 'NS', 'NS', f'{MA}: Clean Inside/Outside of Microwave'), 'cab_fronts': ('INC', 'NS', 'NS', f'{MA}: Clean Exterior Cabinets'),
    'cab_in': ('PAID', 'PAID', 'NS', 'Extras: Clean Inside Cabinets (booking form 13 Oct: $5 per unit)'),
    'fridge_in': ('PAID', 'PAID', 'NS', 'Extras: Clean inside the fridge (booking form 13 Oct: $45)'), 'oven_in': ('PAID', 'PAID', 'NS', 'Extras: Clean inside the oven (booking form 13 Oct: $45)'),
    'dishes': ('PAID', 'PAID', 'NS', 'Booking form extra (13 Oct): dishes $65 (not on the web checklist)'),
    'toilet': ('INC', 'NS', 'INC', f'{MA}: Detail the Porcelain Throne; {MM}: Scrubbing the toilets'), 'tub_shower': ('INC', 'NS', 'INC', f'{MA}: Scrub Showers & Tubs; {MM}: showers, and bathtubs'),
    'b_sink': ('INC', 'NS', 'INC', f'{MA}: Clean Sinks; Polish Fixtures; Clean Vanities'), 'mirrors': ('INC', 'NS', 'NS', f'{MA}: Shine Mirrors'),
    'grout': ('NS', 'NS', 'NS', 'Not listed; terms: "We are not tile, grout ... experts"'),
    'dust': ('INC', 'NS', 'INC', f'{MA}: Dust All Surfaces; {MM}: Dusting everywhere, including the high-to-reach places'),
    'fans': ('INC', 'NS', 'NS', f'{MA}: Detail Ceiling Fans (living room)'), 'cobwebs': ('INC', 'NS', 'NS', f'{MA}: Cobweb Removal'),
    'bb_wipe': ('INC', 'NS', 'INC', f'{MA}: Scrub Baseboards; {MM}: Cleaning the baseboards'),
    'blinds': ('INC', 'NS', 'NS', f'{MA}: Dust & Clean Blinds (Wet Wipe Window Blinds is an extra, $5/unit)'),
    'doors': ('INC', 'NS', 'NS', f'{MA}: Clean Doors & Frames'), 'switches': ('INC', 'NS', 'NS', f'{MA}: Clean Outlets & Light Switches; Sanitize All High-touch Surfaces'),
    'win_in': ('PAID', 'PAID', 'NS', 'Extras: Clean interior of windows (booking form 13 Oct: $5/window)'), 'vents': ('INC', 'NS', 'NS', f'{MA}: Clean Air Vents'),
    'vacuum': ('INC', 'NS', 'INC', f'{MA}: Vacuum Carpets, Stairs, & Rugs; {MM}: Vacuuming the floors'), 'mop': ('INC', 'NS', 'INC', f'{MA}: Vacuum & Mop Floors; {MM}: Scrubbing the ... floors'),
    'stairs': ('INC', 'NS', 'NS', f'{MA}: Vacuum Carpets, Stairs, & Rugs'), 'trash': ('INC', 'NS', 'NS', f'{MA}: Remove Trash'),
    'tidy': ('COND', 'COND', 'COND', 'Terms: home should be de-cluttered; organizing before cleaning is charged as extra time (or $50 refusal fee)'),
    'laundry': ('PAID', 'PAID', 'NS', 'Extras: Laundry & Folding (one load only) (booking form 13 Oct: $65)'),
    'basement': ('PAID', 'PAID', 'NS', 'Extras: Deep cleaning basement (booking form 13 Oct: finished basement $120)'),
    'organize': ('PAID', 'PAID', 'NS', 'Booking form extra (13 Oct): house organization $375'), 'pets': ('PAID', 'PAID', 'NS', 'Booking form (13 Oct): pets $10'),
    'extra_time': ('COND', 'COND', 'COND', 'Terms: if the calculator underestimates, "extend the cleaning at our hourly rate OR extra add-ons will be added"; deep is "billed hourly" as an add-on'),
    'ladder': ('EXC', 'EXC', 'EXC', 'Terms: "not allowed to climb ladders or be on stools of any sort"'),
    'biohazard': ('EXC', 'EXC', 'EXC', 'Terms: may refuse service for "mold, hoarding, abnormal buildup"'),
}

S = 'Standard checklist'
D['Super Cleaning Service Louisville'] = {
    'counters': (*A, f'{S}: All Countertops; Backsplash'), 'k_sink': (*A, f'{S}: Sinks'), 'stovetop': (*A, f'{S}: Stovetop and Stove Fan'),
    'appl_ext': (*A, f'{S}: Dishwasher (Outside Only); Oven (Outside Only); Outside Fridge; Small Appliances; Polish Stainless Steel'),
    'micro_in': ('NS', 'NS', 'NS', f'{S} lists "Microwave" without saying inside or outside'),
    'cab_fronts': ('COND', 'INC', 'INC', 'Standard: "Cabinets - Dusted and Spot Checked"; deep: "Hand Wash Outsides of Cabinets"'),
    'hood': ('COND', 'COND', 'COND', 'Standard: "Stovetop and Stove Fan" (hood not named); deep adds "Kitchen Grease & Buildup Removal"'),
    'cab_in': ('NS', 'NS', 'INC', 'Moving clean: "Inside Empty Cabinets"'),
    'fridge_in': ('PAID', 'PAID', 'PAID', 'Upgrade: (+ $65) Interior of Fridge & Freezer'), 'oven_in': ('PAID', 'PAID', 'PAID', 'Upgrade: (+ $65) Interior of Oven'),
    'toilet': (*A, f'{S}: Toilet'), 'tub_shower': (*A, f'{S}: Shower Stall; Bathtub; Shower Racks (as able)'),
    'b_sink': (*A, f'{S}: Sinks; Countertops; Faucets (also polished)'), 'mirrors': (*A, f'{S}: Mirrors; Clean All Mirrors; Clean All Glass Surfaces'),
    'soap_scum': ('INC', 'INC', 'INC', 'Standard: "Remove Soap Scum"; deep: "Full Soap Scum Buildup Removal"'),
    'dust': (*A, f'{S}: Dust from Top to Bottom; Dust Furniture and Decorations'), 'fans': (*A, f'{S}: Dust Light Fixtures and Fans'), 'fixtures': (*A, f'{S}: Dust Light Fixtures and Fans'),
    'bb_dust': (*A, f'{S}: Dust Baseboards'), 'bb_wipe': ('NS', 'INC', 'INC', 'Deep: "Hand Wash Baseboards"'),
    'sills': (*A, f'{S}: Dust Blinds and Window Sills'), 'blinds': (*A, f'{S}: Dust Blinds and Window Sills'), 'doors': ('NS', 'INC', 'INC', 'Deep: "Hand Wash Wood Trim"'),
    'switches': ('NS', 'NS', 'NS', f'{S}: "Remove Fingerprints/Smudges" (switch plates not named)'),
    'win_in': ('PAID', 'PAID', 'PAID', 'Upgrade: (+ $8 per window) Interior Windows'),
    'upholstery': ('PAID', 'PAID', 'PAID', 'Upgrades: (+ $15) Vacuum Sectional/Large Couch; (+ $10) Vacuum Small Couch'),
    'vacuum': (*A, f'{S}: Vacuum All Floors; Throw Rugs Vacuumed'), 'mop': (*A, f'{S}: Mop Hard Surface Flooring'), 'stairs': (*A, f'{S}: Vacuum Stairs'),
    'beds': (*A, f'{S}: Make Beds'), 'linens': ('PAID', 'PAID', 'PAID', 'Upgrade: (+ $10) Changing Linens'),
    'trash': (*A, f'{S}: Empty Trash'), 'tidy': (*A, f'{S}: Straighten and Make Presentable; Towels Folded and Hung'),
    'extra_time': ('PAID', 'PAID', 'PAID', 'Booking form (Launch27 feed): Additional Time $32.50 per 30 minutes'),
    'move_furn': ('EXC', 'EXC', 'EXC', 'FAQ: "We do not move large furniture"'), 'ladder': ('EXC', 'EXC', 'EXC', 'FAQ: "we do not clean from heights and our teams do not bring ladders"'),
    'biohazard': ('EXC', 'EXC', 'EXC', 'FAQ: "we cannot clean in homes with biohazards such as animal waste and insect/rodent cleanup"'),
    'haul_trash': ('EXC', 'EXC', 'EXC', 'FAQ: "We do not move ... large amounts of trash"'),
}

RS, RD, RMO = 'Standard page', 'Deep page', 'Move-out page'
D['Red Feather Cleaning'] = {
    'counters': ('INC', 'INC', 'INC', f'{RS}: Cleaning and sanitizing countertops, sinks, and stovetops; {RD}: Full sanitization of countertops, sinks, and backsplash; {RMO}: countertops, sinks, and backsplashes'),
    'k_sink': ('INC', 'INC', 'INC', f'{RS}: countertops, sinks, and stovetops'), 'stovetop': ('INC', 'NS', 'INC', f'{RS}: countertops, sinks, and stovetops; {RMO}: Degreasing stovetops and ranges'),
    'appl_ext': ('INC', 'INC', 'INC', f'{RS}: Wiping down exterior surfaces of appliances; {RD}: cleaning the interior and exterior of appliances; {RMO}: Polishing fixtures and appliance exteriors'),
    'micro_in': ('INC', 'NS', 'INC', f'{RS}: Cleaning the inside of microwaves; {RMO}: Cleaning ovens, microwaves, and refrigerators'),
    'fridge_in': ('NS', 'INC', 'INC', f'{RD}: "cleaning the interior and exterior of appliances"; {RMO}: Cleaning ovens, microwaves, and refrigerators'),
    'oven_in': ('NS', 'INC', 'INC', f'{RD}: interior of appliances; {RMO}: Cleaning ovens'),
    'hood': ('NS', 'INC', 'NS', f'{RD}: Degreasing of stove hoods'), 'cab_fronts': ('NS', 'NS', 'INC', f'{RMO}: Wiping cabinets and drawers inside and out'),
    'cab_in': ('NS', 'NS', 'INC', f'{RMO}: Wiping cabinets and drawers inside and out'),
    'toilet': ('INC', 'INC', 'INC', f'{RS}: Scrubbing and sanitizing sinks, countertops, toilets, showers, and tubs'),
    'tub_shower': ('INC', 'INC', 'INC', f'{RS}: showers, and tubs'), 'b_sink': ('INC', 'INC', 'INC', f'{RS}: sinks, countertops; {RMO}: Sanitizing counters, mirrors, and fixtures'),
    'mirrors': ('INC', 'INC', 'INC', f'{RS}: Cleaning mirrors and glass surfaces'), 'grout': ('NS', 'NS', 'INC', f'{RMO}: Cleaning tile grout and walls'),
    'dust': ('INC', 'INC', 'INC', f'{RS}: Dusting all surfaces, including furniture, shelves; {RMO}: Dusting ledges, shelves, and windowsills'),
    'fixtures': ('INC', 'INC', 'INC', f'{RS}: Dusting furniture, light fixtures (dining); {RMO}: Dusting ceiling fans and fixtures'),
    'fans': ('NS', 'INC', 'INC', f'{RD}: Ceiling fans dusted and cleaned; {RMO}: Dusting ceiling fans and fixtures'),
    'cobwebs': ('INC', 'INC', 'INC', f'{RS}: Removing cobwebs from ceilings and corners'),
    'bb_dust': ('INC', 'INC', 'INC', f'{RS}: Dusting all surfaces, including ... baseboards; {RMO}: Dusting vents, ledges, and baseboards'),
    'bb_wipe': ('NS', 'INC', 'INC', f'{RD}: Baseboards cleaned to remove scuffs and grime; {RMO}: Cleaning baseboards and trim'),
    'sills': ('INC', 'NS', 'INC', f'{RS}: Light dusting of window sills and blinds; {RMO}: Dusting ledges, shelves, and windowsills'),
    'blinds': ('INC', 'INC', 'INC', f'{RS}: Light dusting of ... blinds; {RD}: Window blinds cleaned; {RMO}: Dusting blinds and vents'),
    'doors': ('NS', 'NS', 'INC', f'{RMO}: Wiping doors, frames, and light switches'), 'switches': ('NS', 'NS', 'INC', f'{RMO}: Disinfecting light switches and door handles'),
    'walls': ('NS', 'NS', 'INC', f'{RMO}: Cleaning tile grout and walls (bathrooms)'), 'vents': ('NS', 'NS', 'INC', f'{RMO}: Dusting vents; Cleaning baseboards and vents'),
    'closets': ('NS', 'NS', 'COND', f'{RMO}: Checking closets and drawers for debris'),
    'win_in': ('NS', 'NS', 'NS', 'No Red Feather add-on price found (the "+$50–$100" on its move page is a US-average table)'),
    'vacuum': ('INC', 'INC', 'INC', f'{RS}: Vacuuming or sweeping and mopping floors'), 'mop': ('INC', 'INC', 'INC', f'{RS}: Vacuuming or sweeping and mopping floors'),
    'beds': ('INC', 'COND', 'NS', f'{RS}: Making beds and organizing bedding; {RD}: Making beds (if applicable)'),
    'trash': ('INC', 'NS', 'NS', f'{RS}: Emptying trash'), 'tidy': ('INC', 'NS', 'NS', f'{RS}: organizing countertops; organizing bedding'),
    'laundry': ('COND', 'COND', 'NS', f'{RS}: Laundry room – exterior of washer/dryer wiped (no laundry service stated)'),
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

RR, RRD = 'Basic list', 'Deep/move list'
D['Rocking Robins (R&R) Maids'] = {  # deep and move lists are identical; "vacant homes" items apply to move
    'counters': (*A, 'Counter tops & back splashes (washed / hand washed)'), 'k_sink': (*A, 'All sinks (scrubbed/disinfected)'),
    'stovetop': (*A, 'Stove top & drip pans scrubbed / Stove top, grates or drip pans scrubbed'),
    'appl_ext': (*A, 'Outside of appliances cleaned; Top of refrigerator (dusted / hand washed or wiped)'),
    'micro_in': ('NS', 'INC', 'INC', f'{RRD}: Outside of appliances cleaned / inside microwave'),
    'cab_fronts': ('NS', 'INC', 'INC', f'{RRD}: All Cabinet fronts (hand washed or wiped)'),
    'cab_in': ('NS', 'COND', 'COND', f'{RRD}: "Vacant homes: drawers, empty shelves, inside cabinets (hand washed or wiped)"'),
    'fridge_in': ('PAID', 'PAID', 'PAID', 'Optional add-on: Inside refrigerator / Inside freezer (13 Oct calculator: $60 each)'),
    'dishes': ('EXC', 'EXC', 'EXC', '"Dishes are not included."'),
    'toilet': ('NS', 'NS', 'NS', 'Toilets are not named on any R&R list ("All bathroom counters & fixtures (sanitized)")'),
    'tub_shower': (*A, 'Tub/shower & tiles (scrubbed / double scrubbed to remove build-up)'), 'b_sink': (*A, 'All sinks; All bathroom counters & fixtures (sanitized)'),
    'mirrors': (*A, 'Mirrors (Windex-ed / cleaned)'), 'soap_scum': ('NS', 'INC', 'INC', f'{RRD}: Tub/shower & tiles (double scrubbed to remove build-up)'),
    'dust': (*A, 'Furniture (dusted & polished); Pictures & knick-knacks; Lamps & lampshades; Moldings & woodwork'),
    'fans': ('COND', 'COND', 'COND', 'Ceiling fans dusted (basic) / hand washed "within 2-step ladder reach"; vaulted or wobbly fans skipped'),
    'fixtures': ('COND', 'COND', 'COND', 'Light fixtures dusted / hand washed "within 2-step ladder reach"; chandeliers beyond reach not hand-cleaned'),
    'cobwebs': (*A, 'Cobwebs removed'), 'bb_dust': ('INC', 'INC', 'INC', 'Baseboards (dusted)'),
    'bb_wipe': ('NS', 'COND', 'COND', f'{RRD}: Baseboards (hand washed or wiped, reachable w/out moving furniture)'),
    'sills': (*A, 'Window frames, & lock ledges (dusted / hand washed or wiped)'),
    'blinds': ('PAID', 'PAID', 'PAID', 'Not on the web lists; 13 Oct calculator extra: blinds $20 each'),
    'doors': ('NS', 'INC', 'INC', f'{RRD}: All Doors and door frames (hand washed or wiped)'), 'switches': ('NS', 'INC', 'INC', f'{RRD}: Light switch plates (hand washed)'),
    'win_in': ('PAID', 'PAID', 'PAID', 'Optional add-on: Interior windows (13 Oct calculator: $5 each)'),
    'vacuum': (*A, 'Floors (vacuumed &/or mopped)'), 'mop': (*A, 'Floors (vacuumed &/or mopped)'), 'stairs': (*A, 'Stairs (vacuumed, wood dusted)'),
    'trash': (*A, 'Wastebaskets (emptied/washed/relined)'),
    'closets': ('EXC', 'EXC', 'COND', '"We do not clean closets ... unless the cleaning is a move in or out"; "Vacant homes: inside of closets and laundry rooms"'),
    'laundry': ('EXC', 'EXC', 'COND', '"We do not clean ... laundry rooms ... unless ... move in or out" (laundry rooms, not laundry service)'),
    'basement': ('COND', 'COND', 'COND', 'Unfinished areas excluded unless move ("We do not clean ... unfinished areas unless the cleaning is a move in or out"); the 13 Oct calculator adds hours for a basement'),
    'extra_time': ('COND', 'COND', 'COND', 'FAQ: "Additional tasks may require extra time"; deep prices depend on "condition, layout, and time required"'),
    'move_furn': ('EXC', 'EXC', 'EXC', '"We cannot move furniture" / "We do not move heavy furniture"'), 'ladder': ('EXC', 'EXC', 'EXC', '"We do not climb higher than a 2-step ladder."'),
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

SR, SD, SM = 'Regular page', 'Deep page', 'Move page'
D['Stitch Cleaning'] = {  # regular list is 4 generic lines; first visit of a regular plan is a deep clean
    'dust': ('INC', 'INC', 'INC', f'{SR}: Dusting and wiping down all surfaces; {SD}: We dust, vacuum, and polish surfaces; {SM}: Dusting all surfaces'),
    'vacuum': ('INC', 'INC', 'INC', f'{SR}: Sweeping, mopping, and vacuuming floors'), 'mop': ('INC', 'NS', 'INC', f'{SR}: Sweeping, mopping, and vacuuming floors; {SM}: Mopping and vacuuming floors'),
    'tidy': ('INC', 'NS', 'NS', f'{SR}: General tidying of living spaces and bedrooms'),
    'counters': ('NS', 'INC', 'INC', f'{SR} says only "Sanitizing kitchens and bathrooms"; {SD}: countertops; {SM}: Cleaning and sanitizing countertops and backsplashes'),
    'k_sink': ('NS', 'INC', 'NS', f'{SD}: We clean countertops, sinks, appliances, and cabinets'),
    'appl_ext': ('NS', 'COND', 'INC', f'{SD}: "appliances" (inside/outside not stated); {SM}: Cleaning appliance exteriors (interior cleaning optional)'),
    'cab_fronts': ('NS', 'COND', 'INC', f'{SD}: "cabinets" (fronts/inside not stated); {SM}: Wiping down cabinet fronts and exteriors'),
    'hood': ('NS', 'NS', 'INC', f'{SM}: Degreasing stovetops, ovens, and range hoods'), 'stovetop': ('NS', 'NS', 'INC', f'{SM}: Degreasing stovetops'),
    'oven_in': ('NS', 'NS', 'COND', f'{SM}: "Degreasing stovetops, ovens" + "interior cleaning optional"; move-out: "Appliance cleaning upon request"'),
    'fridge_in': ('NS', 'NS', 'COND', f'{SM}: "Cleaning appliance exteriors (interior cleaning optional)"'),
    'toilet': ('NS', 'INC', 'INC', f'{SD}: from toilets and showers to sinks and mirrors; {SM}: Scrubbing and disinfecting toilets'),
    'tub_shower': ('NS', 'INC', 'INC', f'{SD}: toilets and showers; {SM}: Cleaning showers, tiles, and mirrors; bathtubs'),
    'mirrors': ('NS', 'INC', 'INC', f'{SD}/{SM}: mirrors'), 'b_sink': ('NS', 'INC', 'INC', f'{SD}: sinks; {SM}: Polishing chrome fixtures; Sanitizing countertops'),
    'fans': ('NS', 'INC', 'NS', f'{SD}: we clean high shelves, ceiling fans, and light fixtures'), 'fixtures': ('NS', 'INC', 'INC', f'{SD}: light fixtures; {SM}: Dusting all surfaces and fixtures'),
    'blinds': ('NS', 'INC', 'NS', f'{SD}: We wash windows, wipe down blinds, and clean tracks'), 'win_in': ('NS', 'INC', 'NS', f'{SD}: We wash windows ... and clean tracks (interior/exterior not stated)'),
    'under_furn': ('NS', 'INC', 'NS', f'{SD}: reaching hidden spots behind or under furniture'),
    'bb_wipe': ('NS', 'NS', 'INC', f'{SM}: Wiping down baseboards and light switches'), 'sills': ('NS', 'NS', 'INC', f'{SM}: Dusting all surfaces, including windowsills and frames'),
    'switches': ('NS', 'NS', 'INC', f'{SM}: Wiping down baseboards and light switches'),
    'biohazard': ('EXC', 'EXC', 'EXC', f'{SM} FAQ: "we don\'t clean hazardous materials, heavily damaged areas, or inaccessible spaces"'),
    'extra_time': ('PAID', 'NS', 'COND', f'{SR} FAQ: deep-cleaning tasks can be added "for an additional cost"; {SM}: "additional time may be needed to work around furniture or boxes"'),
}

HS, HD, HMI, HMO = 'Louisville standard list', 'Deep checklist', 'Move-in checklist', 'Move-out checklist'
D['Hello Cleaners'] = {
    'counters': ('INC', 'INC', 'INC', f'{HS}: Countertops, sink and faucets cleaned and descaled; {HD}: Deep-clean kitchen counters and backsplash; {HMI}: Degrease and sanitize kitchen surfaces'),
    'k_sink': ('INC', 'NS', 'NS', f'{HS}: Countertops, sink and faucets cleaned and descaled'), 'stovetop': ('INC', 'NS', 'NS', f'{HS}: Stovetop, backsplash and appliance exteriors degreased'),
    'appl_ext': ('INC', 'NS', 'NS', f'{HS}: Stovetop, backsplash and appliance exteriors degreased'),
    'cab_fronts': ('INC', 'INC', 'INC', f'{HS}: Cabinet fronts, handles and trash cans wiped out; {HD}: Wipe cabinet fronts inside and out; {HMO}: Scrub all cabinets inside and out'),
    'cab_in': ('NS', 'INC', 'INC', f'{HD}: Wipe cabinet fronts inside and out; {HMI}: Clean inside all cabinets and drawers'),
    'fridge_in': ('PAID', 'PAID', 'INC', f'Add-on: Inside Fridge (no price); {HMI}: Clean inside the refrigerator; {HMO}: Clean inside and behind the refrigerator'),
    'oven_in': ('PAID', 'PAID', 'INC', f'Add-on: Inside Oven (no price); {HMO}: Deep-clean and degrease the oven'),
    'toilet': ('INC', 'INC', 'INC', f'{HS}: Toilet, sink and bathtub sanitized inside and out; {HD}: Scrub and disinfect all bathrooms'),
    'tub_shower': ('INC', 'INC', 'INC', f'{HS}: Toilet, sink and bathtub sanitized; Shower door, tiles and grout treated; {HD}: Descale showers, tubs, tiles and fixtures'),
    'b_sink': ('INC', 'INC', 'INC', f'{HS}: sink ... sanitized; Mirrors, chrome and fittings polished'), 'mirrors': ('INC', 'NS', 'NS', f'{HS}: Mirrors, chrome and fittings polished streak-free'),
    'grout': ('COND', 'NS', 'INC', f'{HS}: "grout treated for soap and hard-water buildup" (FAQ says "detailed grout" is deep-only); {HMO}: Scrub grout and remove mold'),
    'soap_scum': ('INC', 'INC', 'INC', f'{HS}: treated for soap and hard-water buildup; {HD}: Descale showers ...; {HMO}: Remove hard-water scale'),
    'dust': ('INC', 'INC', 'NS', f'{HS}: Dusting from high surfaces down, including shelves and sills; {HD}: Dust and wipe all surfaces'),
    'sills': ('INC', 'INC', 'NS', f'{HS}: including shelves and sills; {HD}: Clean interior windows and sills'),
    'fans': ('NS', 'INC', 'NS', f'{HD}: Clean light fixtures and ceiling fans'), 'fixtures': ('NS', 'INC', 'NS', f'{HD}: Clean light fixtures and ceiling fans'),
    'cobwebs': ('NS', 'INC', 'NS', f'{HD}: Remove cobwebs and dust vents'),
    'bb_dust': ('NS', 'NS', 'INC', f'{HMI}: Dust walls, baseboards and vents'), 'bb_wipe': ('NS', 'INC', 'INC', f'{HD}: Hand-clean baseboards, trim and door frames; {HMO}: Hand-clean baseboards and trim'),
    'doors': ('INC', 'INC', 'NS', f'{HS}: Switches, handles and door frames wiped; {HD}: door frames'),
    'switches': ('INC', 'INC', 'INC', f'{HS}: Switches, handles and door frames wiped; {HD}: Detail switches, handles; {HMO}: Spot-clean walls and light switches'),
    'win_in': ('PAID', 'INC', 'INC', f'Add-on: Interior Windows (no price); {HD}: Clean interior windows and sills; {HMI}/{HMO}: interior windows and tracks'),
    'walls': ('PAID', 'PAID', 'INC', f'Add-on: Wall Spot-Clean (no price); {HMO}: Spot-clean walls'), 'vents': ('NS', 'INC', 'INC', f'{HD}: dust vents; {HMI}: Dust walls, baseboards and vents'),
    'vacuum': ('INC', 'INC', 'INC', f'{HS}: Floors vacuumed and hard floors washed'), 'mop': ('INC', 'INC', 'INC', f'{HS}: hard floors washed; {HD}: Vacuum and mop all floors'),
    'closets': ('NS', 'NS', 'INC', f'{HMI}: Wipe down all shelving and closets; {HMO}: Clean inside closets and storage'),
    'trash': ('NS', 'INC', 'INC', f'{HS}: trash cans wiped out (emptying not stated); {HD}: Empty trash and reset each room; {HMO}: Remove all trash and debris'),
    'tidy': ('NS', 'INC', 'NS', f'{HD}: Empty trash and reset each room'), 'laundry': ('PAID', 'PAID', 'NS', 'Add-on: Laundry (Wash, dry and fold) (no price)'),
    'organize': ('PAID', 'PAID', 'PAID', 'Separate service: Organizing & Decluttering from $160 per visit'),
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
CLX = 'FAQ: "Additional services such as inside refrigerator, oven, interior windows, inside cabinets, laundry ... for an additional charge" (no prices)'
D['Cleanoria (Thumbtack)'] = {'win_in': ('PAID', 'PAID', 'PAID', CLX), 'fridge_in': ('PAID', 'PAID', 'PAID', CLX), 'oven_in': ('PAID', 'PAID', 'PAID', CLX),
                              'cab_in': ('PAID', 'PAID', 'PAID', CLX), 'laundry': ('PAID', 'PAID', 'PAID', CLX),
                              'pets': ('COND', 'COND', 'COND', 'Services list: "Pets: Houses with pets" (no surcharge stated)')}

TIERS = ('standard', 'deep', 'move')
rows = []
for co, meta in CO.items():
    tasks = D[co]
    bad = set(tasks) - set(TASK_IDS)
    assert not bad, (co, bad)
    for area, tid, label in TASKS:
        st, dp, mv, txt = tasks.get(tid, ('NS', 'NS', 'NS', ''))
        rows.append(dict(company=co, louisville_conclusions=meta.get('louisville', 'included'), area=area, task_id=tid, task=label, standard=st, deep=dp, move=mv,
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
LOU = [c for c in cos if not CO[c].get('louisville', 'included').startswith('EXCLUDED')]  # Louisville conclusions exclude national platforms
PRICED = ['Scrub Lou', 'Maids in Apron', 'Super Cleaning Service Louisville', 'Red Feather Cleaning', 'Maid 2 Clean KY']
summ = []
for area, tid, label in TASKS:
    c = Counter(); cp = Counter(); paid_prices = []
    for co in LOU:
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
