"""Regenerate audit/exports/hfal-compliance-tracker.xlsx from tracker.csv.
Usage: python audit/scripts/build_xlsx.py

Highlighting: yellow = changed in that hospital's last update (comment shows the previous value);
grey = not verified in the latest check (comment shows the last value recorded in the changelog)."""
import copy, csv
import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill, Alignment
from openpyxl.worksheet.table import TableColumn
from openpyxl.utils import column_index_from_string as ci
from lib import AUDIT, CHANGELOG, COLUMNS, GRADED, LETTERS, read_tracker, config

TEMPLATE = AUDIT / 'template' / 'hfal-template.xlsx'
OUT = AUDIT / 'exports' / 'hfal-compliance-tracker.xlsx'
CHANGED = PatternFill('solid', fgColor='FFE699')
UNVER = PatternFill('solid', fgColor='D9D9D9')
NOFILL = PatternFill(fill_type=None)
FORMULAS = {'O', 'P', 'Q', 'AV', 'AY'}         # kept from the template (live formulas)

rows = read_tracker()
cfg = config()
log = list(csv.DictReader(CHANGELOG.open(encoding='utf-8'))) if CHANGELOG.exists() else []
last_change = {}                  # (hospital_id, col) -> most recent real change
last_value = {}                   # (hospital_id, col) -> last non-blank value recorded
for e in log:
    k = (e['hospital_id'], e['column'])
    if e['new_value'] != '(blank)':
        last_change[k] = e
        last_value[k] = e['new_value']
    elif e['old_value'] != '(blank)':
        last_value.setdefault(k, e['old_value'])

wb = openpyxl.load_workbook(TEMPLATE)
ws = wb['Hospital Tracker']
hdr_style = ws['AQ2']
headers = dict(COLUMNS)
headers['AH'] = f"{cfg['fpl_year']} FPL Guidelines"
for col in LETTERS:
    c = ws[f'{col}2']
    if ci(col) >= ci('AR') or col == 'AH':
        c.value = headers[col]
        for attr in ('font', 'fill', 'alignment', 'border'):
            setattr(c, attr, copy.copy(getattr(hdr_style, attr)))
ws.column_dimensions['AZ'].width = 14
ws.column_dimensions['BA'].width = 14
t = ws.tables['Table1']
t.ref = f'A2:BA{len(rows) + 2}'
names = [headers[col] for col in LETTERS]
t.tableColumns = [TableColumn(id=i + 1, name=n) for i, n in enumerate(names)]
t.autoFilter.ref = t.ref

font = copy.copy(ws['R3'].font)
for i, row in enumerate(rows):
    r = i + 3
    for col in LETTERS:
        if col in FORMULAS:
            continue
        v = row[col]
        cell = ws[f'{col}{r}']
        if col == 'AI' and v not in ('', 'no'):
            v = float(v); v = int(v) if v.is_integer() else v
        elif col == 'AX':
            v = int(v) if v not in ('', None) else 0
        elif col in ('G', 'I', 'J', 'K') and v.isdigit() and not v.startswith('0'):
            v = int(v)                       # numeric ids/zips stay numbers, as in the original sheet
        elif col == 'AP' and v in ('True', 'False'):
            v = (v == 'True')
        cell.value = v if v != '' else None
        if ci(col) >= ci('AR'):
            cell.font = font
            cell.alignment = Alignment(vertical='top')
    for col in GRADED:
        cell = ws[f'{col}{r}']
        cell.fill = NOFILL
        cell.comment = None
        k = (row['hospital_id'], col)
        if row[col] == '':
            cell.fill = UNVER
            prev = last_value.get(k)
            cell.comment = Comment(f"Not verified on {row['BA']}." + (f" Last recorded value: {prev}" if prev else ''),
                                   'HFAL audit')
        elif k in last_change and last_change[k]['date'] == row['AZ']:
            e = last_change[k]
            cell.fill = CHANGED
            cell.comment = Comment(f"Changed {e['date']}. Previous value: {e['old_value']}", 'HFAL audit')
    ws[f'AV{r}'] = f'=IF(AS{r}="None","Final","Provisional - blank cells not counted")'
    ws[f'AY{r}'] = row['AY'] or 'No change'

wb.calculation.fullCalcOnLoad = True
OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print('wrote', OUT.relative_to(AUDIT.parent), len(rows), 'hospitals')
