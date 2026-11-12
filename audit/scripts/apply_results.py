"""Apply one audit run's findings to tracker.csv and changelog.csv.
Usage: python audit/scripts/apply_results.py <results.json> [--date YYYY-MM-DD]

results.json is a list of objects, one per hospital (schema in audit/AUDIT_INSTRUCTIONS.md).
Rules:
  * A graded field whose value changes is logged in changelog.csv and bumps "Last Updated".
  * A field the agent could not verify (null) is left blank and listed in "Unverified Columns";
    this is logged with note "unverified this run" but does NOT count as a data change.
  * "Last Checked" is set for every hospital in the run.
Writes the raw findings to audit/runs/<run_id>.json and a commit summary to audit/work/summary.md."""
import argparse, csv, datetime, json, sys
from openpyxl.utils import column_index_from_string as ci
from lib import (AUDIT, CHANGELOG, COLUMNS, BINARY, GRADED, TEXT, read_tracker, write_tracker, grade, norm)

ap = argparse.ArgumentParser()
ap.add_argument('results')
ap.add_argument('--date', default=datetime.date.today().isoformat())
a = ap.parse_args()
date = a.date
run_id = f'{date}-run'
existing = sorted((AUDIT / 'runs').glob(f'{date}-run*.json'))
if existing:
    run_id = f'{date}-run{len(existing) + 1}'

results = json.load(open(a.results))
rows = read_tracker()
by_id = {r['hospital_id']: r for r in rows}

errors = []
for d in results:
    if d.get('hospital_id') not in by_id:
        errors.append(f"unknown hospital_id {d.get('hospital_id')!r}")
    for c in BINARY:
        v = d.get(c)
        if v is not None and norm(v) not in ('yes', 'no'):
            errors.append(f"{d.get('hospital_id')} {c}={v!r} (must be yes/no/null)")
    m = d.get('max_fpl_percent')
    if m is not None and not isinstance(m, (int, float)):
        errors.append(f"{d.get('hospital_id')} max_fpl_percent={m!r} (must be number/null)")
if errors:
    sys.exit('Refusing to apply results:\n  ' + '\n  '.join(errors))


def fmt_ai(v):
    try:
        return f'{int(round(float(v) * 100))}%'
    except (TypeError, ValueError):
        return norm(v) or '(blank)'


log, summary = [], []
for d in results:
    row = by_id[d['hospital_id']]
    before_grade = row['O']
    new = {c: (norm(d.get(c)) if d.get(c) is not None else '') for c in BINARY}
    m = d.get('max_fpl_percent')
    if m is None:
        new['AI'] = ''
    else:
        m = float(m)
        new['AI'] = (f'{m / 100:g}' if m >= 400 else 'no')
    unverified = {str(u).strip().upper() for u in (d.get('unverified') or [])}
    unverified = {'AI' if u in ('MAX_FPL_PERCENT', 'MAX FPL') else u for u in unverified}
    unverified |= {c for c in GRADED if new[c] == ''}

    changes = []
    for c in GRADED:
        old, nv = norm(row[c]), new[c]
        same = (old == nv) or (c == 'AI' and nv == 'no' and old not in ('', 'no') and float(old) < 4)
        if same:
            continue
        if nv == '':
            log.append([date, run_id, row['hospital_id'], row['A'], row['M'], c, COLUMNS[c],
                        fmt_ai(old) if c == 'AI' else (old or '(blank)'), '(blank)', 'unverified this run'])
        else:
            o = fmt_ai(old) if c == 'AI' else (old or '(blank)')
            n_ = (f'no ({int(m)}%)' if nv == 'no' else fmt_ai(nv)) if c == 'AI' else nv
            changes.append(f'{c} {COLUMNS[c]}: {o} -> {n_}')
            log.append([date, run_id, row['hospital_id'], row['A'], row['M'], c, COLUMNS[c], o, n_,
                        (d.get('changes_vs_previous') or '')[:300]])
        row[c] = nv

    for c in TEXT:
        if d.get(c) not in (None, ''):
            row[c] = str(d[c])
    row['AS'] = ', '.join(sorted(unverified, key=ci)) or 'None'
    row['AT'] = d.get('changes_vs_previous') or ''
    row['AU'] = '\n'.join(d.get('sources') or [])
    row['AV'] = 'Final' if row['AS'] == 'None' else 'Provisional - blank cells not counted'
    g, auto_f, n = grade(row)
    row['O'], row['P'], row['Q'] = g, str(auto_f).upper(), str(n)
    row['BA'] = date
    if changes:
        row['AR'] = before_grade
        row['AW'] = '; '.join(changes)
        row['AX'] = str(len(changes))
        row['AY'] = 'No change' if g == before_grade else f'{before_grade} -> {g}'
        row['AZ'] = date
        summary.append(f"- {row['A']} ({row['M']}): {row['AY']}; {len(changes)} field(s): " +
                       '; '.join(x.split(':')[0] for x in changes))

write_tracker(rows)
new_file = not CHANGELOG.exists()
with CHANGELOG.open('a', newline='', encoding='utf-8') as f:
    w = csv.writer(f, lineterminator='\n')
    if new_file:
        w.writerow(['date', 'run_id', 'hospital_id', 'hospital', 'system', 'column', 'field', 'old_value', 'new_value', 'note'])
    w.writerows(log)
(AUDIT / 'runs').mkdir(exist_ok=True)
(AUDIT / 'runs' / f'{run_id}.json').write_text(json.dumps(results, indent=1))

systems = sorted({by_id[d['hospital_id']]['M'] for d in results})
updated = len(summary)
head = (f'Audit {run_id}: {len(results)} hospitals checked in {len(systems)} systems, '
        f'{updated} updated')
body = '\n'.join(summary) or '- No graded fields changed.'
(AUDIT / 'work').mkdir(exist_ok=True)
(AUDIT / 'work' / 'summary.md').write_text(f'{head}\n\nSystems: {", ".join(systems)}\n\n{body}\n')
print(head); print(body)
