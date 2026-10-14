"""Like-for-like check of the five Louisville instant-price companies (added 14 Oct evening).

Same home (exact bed / bath split / sq ft band containing the profile), same service (standard / deep / move),
same visit type (one-time = the first and only visit; recurring = first visit and ongoing reported separately),
and an explicit tax basis:
  * pre-tax      - the four companies whose forms add 6% KY sales tax are shown before tax;
                   Maid 2 Clean shows no tax line, so its displayed price is used as-is ("no tax displayed; treatment unconfirmed").
  * customer-pays - the four x 1.06 (tax shown on their forms) vs Maid 2 Clean as displayed.
Medians are reported with and without Maid 2 Clean so its unconfirmed tax treatment can be judged.
"""
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / 'data'
p = pd.read_csv(DATA / 'profile_prices_all.csv', low_memory=False)

CO = [('scrub-lou', 'Scrub Lou', 'tax added at checkout: 6% (live form)'),
      ('maids-in-apron', 'Maids in Apron', 'displayed total includes 6%; shown here / 1.06'),
      ('super-cleaning-louisville', 'Super Cleaning', 'tax added at checkout: 6% (live form, 14 Oct)'),
      ('redfeathercleaning', 'Red Feather', 'tax added at checkout: 6% (live form, 14 Oct)'),
      ('maid2cleanky', 'Maid 2 Clean', 'no tax displayed; treatment unconfirmed')]
TAXED = {'scrub-lou', 'maids-in-apron', 'super-cleaning-louisville', 'redfeathercleaning'}
CASES = [('standard', 'one_time', 'first'), ('standard', 'biweekly', 'first'), ('standard', 'biweekly', 'ongoing'),
         ('deep', 'one_time', 'first'), ('move_in_out', 'one_time', 'first')]

rows = []
for pid in [f'P{i}' for i in range(1, 11)]:
    for svc, freq, which in CASES:
        r = dict(profile=pid, service=svc, frequency=freq, visit='first visit' if which == 'first' else 'ongoing (later) visits')
        pre, paid, notes = {}, {}, []
        for cid, name, taxnote in CO:
            x = p[(p.company_id == cid) & (p.profile == pid) & (p.service == svc) & (p.frequency == freq)]
            v = np.nan
            if len(x):
                # Maids in Apron has a harvest row (deep/move not offered as a service) AND a model row (add-on); prefer the priced row
                col = 'first_visit_pretax' if which == 'first' else 'ongoing_visit_pretax'
                x = x.assign(_has=x[col].notna()).sort_values('_has', ascending=False).iloc[0]
                r['profile_label'] = x.profile_label
                v = x.first_visit_pretax if which == 'first' else x.ongoing_visit_pretax
                if which == 'first' and not pd.isna(x.get('first_visit_max')) and x.first_visit_max != x.first_visit_pretax:
                    notes.append(f'{name}: {x.first_visit_pretax:.0f}-{x.first_visit_max:.0f} (sq ft band boundary; lowest used)')
            r[f'{name} pre-tax'] = v
            pre[name] = v
            paid[name] = v * 1.06 if (cid in TAXED and not pd.isna(v)) else v
        vals5 = [v for v in pre.values() if not pd.isna(v)]
        vals4 = [v for k, v in pre.items() if k != 'Maid 2 Clean' and not pd.isna(v)]
        paid5 = [v for v in paid.values() if not pd.isna(v)]
        r.update(n5=len(vals5), median5_pretax=np.median(vals5) if vals5 else np.nan,
                 n4_excl_m2c=len(vals4), median4_pretax_excl_m2c=np.median(vals4) if vals4 else np.nan,
                 median5_customer_pays=np.median(paid5) if paid5 else np.nan,
                 m2c_is_lowest=(not pd.isna(pre['Maid 2 Clean'])) and all(pre['Maid 2 Clean'] <= v for v in vals5),
                 notes='; '.join(notes))
        rows.append(r)
out = pd.DataFrame(rows)
cols = ['profile', 'profile_label', 'service', 'frequency', 'visit'] + [f'{n} pre-tax' for _, n, _ in CO] + \
       ['n5', 'median5_pretax', 'n4_excl_m2c', 'median4_pretax_excl_m2c', 'median5_customer_pays', 'm2c_is_lowest', 'notes']
out = out[cols]
out.to_csv(DATA / 'louisville_five_company_basis.csv', index=False)
pd.DataFrame(CO, columns=['company_id', 'company', 'tax_treatment']).to_csv(DATA / 'louisville_tax_basis.csv', index=False)
x = out[(out.service == 'standard') & (out.frequency == 'one_time')]
print(x[['profile', 'n5', 'median5_pretax', 'median4_pretax_excl_m2c', 'median5_customer_pays', 'm2c_is_lowest', 'notes']].round(2).to_string())
