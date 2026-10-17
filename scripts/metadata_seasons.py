"""Seasons from interpretation metadata, for the sens-metadata-seasons run.

    python scripts/metadata_seasons.py <lipdverse.duckdb> <members.csv> <out.yml>

For each member record, the season of its best-ranked climate interpretation
of temperature (for the PSM's tas term) and of moisture (for pr), in cfr's
convention (months 1-12; previous-year months negative, so Sep-Aug is
[-9, -10, -11, -12, 1, ..., 8]). Named seasons follow the record's hemisphere.
Seasons that carry no months ("subannual", "wet season", missing) are left
out, and the run calibrates those records on the class-based pool as before.

Writes metadata_season_dict: {TSid: {tas: [...], pr: [...]}} and a review
table of every seasonality string and its parsed months (<out>.csv).
"""
import re
import sys

import duckdb
import pandas as pd
import yaml

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
INITIALS = 'jfmamjjasond'

# Same classes as cfr_main_code.py's interpretation screen.
CLASSES = [
    (r'isotope|deuterium|excess|d18o|dd$', None),
    (r'temp|^sst$|^t$|degree.?day', 'tas'),
    (r'vpd|vapou?r.?pressure.?deficit|aridity|evapo', 'pr'),
    (r'drought', 'pr'),
    (r'precip|moisture|pdsi|spei|^spi$|humid|^p-e$|^p_e$|rain|streamflow|runoff|wet', 'pr'),
]


def psm_var(variable):
    v = str(variable or '').lower().strip()
    for pat, var in CLASSES:
        if re.search(pat, v):
            return var
    return None


def month(tok):
    tok = tok.lower().strip('. ')
    for i, m in enumerate(MONTHS):
        if tok.startswith(m) and len(tok) >= 3:
            return i + 1
    return None


def initials(tok):
    """'jas' -> [7, 8, 9]; 'djf' -> [12, 1, 2]; None if not a run of months."""
    tok = tok.lower()
    if not (2 <= len(tok) <= 12) or any(c not in INITIALS for c in tok):
        return None
    for start in range(12):
        if all(INITIALS[(start + k) % 12] == c for k, c in enumerate(tok)):
            return [(start + k) % 12 + 1 for k in range(len(tok))]
    return None


def span(m1, m2):
    """Months m1..m2; a span that wraps the year starts in the previous year."""
    if m1 <= m2:
        return list(range(m1, m2 + 1))
    return [-m for m in range(m1, 13)] + list(range(1, m2 + 1))


def wrap_prev(ms):
    """A run of months that wraps December belongs to the previous year up to December."""
    if any(b < a for a, b in zip(ms, ms[1:])):
        cut = next(i for i, (a, b) in enumerate(zip(ms, ms[1:])) if b < a) + 1
        return [-m for m in ms[:cut]] + ms[cut:]
    return ms


def parse(s, lat):
    if s is None:
        return None
    t = str(s).strip().lower().replace('–', '-').replace('—', '-')
    if t in ('', 'nan', 'na', 'none', 'subannual', 'wet season', 'dry season'):
        return None
    if t in ('annual', 'annual (all)', 'year-round', 'mean annual'):
        return list(range(1, 13))
    nh = lat is None or lat >= 0
    named = {
        'summer': [6, 7, 8] if nh else [-12, 1, 2],
        'warm season': [6, 7, 8] if nh else [-12, 1, 2],
        'winter': [-12, 1, 2] if nh else [6, 7, 8],
        'cold season': [-12, 1, 2] if nh else [6, 7, 8],
        'spring': [3, 4, 5] if nh else [9, 10, 11],
        'fall': [9, 10, 11] if nh else [3, 4, 5],
        'autumn': [9, 10, 11] if nh else [3, 4, 5],
        'growing season': [4, 5, 6, 7, 8, 9] if nh else [-10, -11, -12, 1, 2, 3],
    }
    if t in named:
        return named[t]
    # previous-year forms: "prevSep-Aug", "previous September",
    # "previousJAS-currentJJ", "previousOct-currentJuly"
    m = re.match(r'^prev(?:ious)?\s*([a-z]+)(?:\s*-\s*(?:current\s*)?([a-z]+))?$', t)
    if m:
        a, b = m.group(1), m.group(2)
        prev = initials(a) if month(a) is None else [month(a)]
        if prev is None:
            return None
        if b is None:
            return [-x for x in prev]
        cur = initials(b) if month(b) is None else None
        if cur is None:
            mb = month(b)
            if mb is None:
                return None
            if len(prev) == 1:      # prevSep-Aug: previous Sep through current Aug
                return [-x for x in range(prev[0], 13)] + list(range(1, mb + 1))
            cur = list(range(1, mb + 1))
        return [-x for x in prev] + cur
    m = re.match(r'^([a-z]+)\s*-\s*([a-z]+)$', t)
    if m and month(m.group(1)) and month(m.group(2)):
        return span(month(m.group(1)), month(m.group(2)))
    if month(t) and len(t) <= 9:
        return [month(t)]
    ms = initials(t)
    if ms:
        return wrap_prev(ms)
    return None


def main(db, members_csv, out):
    c = duckdb.connect(db, read_only=True)
    mem = pd.read_csv(members_csv)
    c.register('m', mem[['TSid']])
    q = c.execute("""
        select i.TSid, i.rank, i.variable, i.seasonality, t.lat
        from interpretations i join m using (TSid)
        left join (select TSid, any_value(geo_latitude) lat from v_timeseries_full group by 1) t using (TSid)
        where coalesce(lower(i.scope), 'climate') = 'climate'
    """).df() if 'geo_latitude' in [r[0] for r in c.execute('describe v_timeseries_full').fetchall()] else None
    if q is None:
        raise SystemExit('v_timeseries_full has no geo_latitude column; adjust the query')
    q['var'] = q.variable.map(psm_var)
    q['months'] = [parse(s, la) for s, la in zip(q.seasonality, q.lat)]
    review = (q.assign(months=q.months.map(lambda x: '' if x is None else str(x)))
              .groupby(['seasonality', 'months'], dropna=False).size().reset_index(name='n')
              .sort_values('n', ascending=False))
    review.to_csv(out.replace('.yml', '.csv'), index=False)
    q = q[q['var'].notna() & q.months.notna()].sort_values(['TSid', 'rank'], na_position='last')
    d = {}
    for (tsid, var), g in q.groupby(['TSid', 'var'], sort=False):
        d.setdefault(str(tsid), {})[var] = [int(x) for x in g.months.iloc[0]]
    with open(out, 'w') as f:
        f.write('# Seasons from interpretation metadata (scripts/metadata_seasons.py), '
                f'{len(d)} of {len(mem)} member records\n')
        yaml.safe_dump({'metadata_season_dict': d}, f, default_flow_style=None, sort_keys=True)
    print(f'{len(d)} records with a metadata season; '
          f"tas {sum('tas' in v for v in d.values())}, pr {sum('pr' in v for v in d.values())}")


if __name__ == '__main__':
    main(*sys.argv[1:4])
