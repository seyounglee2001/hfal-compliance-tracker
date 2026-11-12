"""One-time import of the November 2026 audit spreadsheet into tracker.csv + changelog.csv.
Usage: python audit/scripts/seed_from_xlsx.py <audit.xlsx> <YYYY-MM-DD>"""
import csv, sys
import openpyxl
from openpyxl.utils import column_index_from_string as ci
from lib import LETTERS, COLUMNS, CHANGELOG, hospital_id, write_tracker, grade, norm

src, date = sys.argv[1], sys.argv[2]
ws = openpyxl.load_workbook(src, data_only=True)['Hospital Tracker']
rows, log = [], []
for r in range(3, ws.max_row + 1):
    if not ws[f'A{r}'].value:
        continue
    row = {k: ws.cell(r, ci(k)).value for k in LETTERS if k not in ('AZ', 'BA')}
    row = {k: ('' if v is None else v) for k, v in row.items()}
    row['hospital_id'] = hospital_id(row['L'], row['A'])
    g, af, n = grade(row)
    assert g == row['O'], (r, g, row['O'])          # Python grade must match the sheet formulas
    row['AZ'] = date; row['BA'] = date
    for item in str(row['AW']).split('; '):
        if item and item != 'None':
            col, rest = item.split(' ', 1)
            field, change = rest.rsplit(': ', 1)
            old, new = change.split(' -> ')
            log.append([date, f'{date}-initial', row['hospital_id'], row['A'], row['M'], col, COLUMNS[col], old, new,
                        'Nov 2026 re-audit vs Sept 2025 CSSNY baseline'])
    rows.append(row)
write_tracker(rows)
with CHANGELOG.open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(['date', 'run_id', 'hospital_id', 'hospital', 'system', 'column', 'field', 'old_value', 'new_value', 'note'])
    w.writerows(log)
print(len(rows), 'hospitals;', len(log), 'changelog entries')
