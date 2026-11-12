"""Shared helpers for the Claude HFAL audit layer.

The source of truth is audit/tracker.csv (one row per hospital, diffable in git).
Every graded-field change is appended to audit/changelog.csv. The spreadsheet in
audit/exports/ is regenerated from the CSV and is never edited by hand.
"""
import csv, hashlib, json
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[1]
TRACKER = AUDIT / 'tracker.csv'
CHANGELOG = AUDIT / 'changelog.csv'
CONFIG = AUDIT / 'config.json'

# Spreadsheet columns A..AY in order, plus the two date columns.
COLUMNS = {
    'A': 'Hospital Name', 'B': 'HYPERLINKED hospital names', 'C': 'Address', 'D': 'City', 'E': 'NYC?',
    'F': 'State', 'G': 'Zip', 'H': 'Operating certificate number',
    'I': 'CMS Certification number (CCN)/Medical provider number (MPN)', 'J': 'Permanent Facility Identifier (PFI)',
    'K': 'OCN_num', 'L': 'OCN_PFI', 'M': 'System', 'N': 'HFA Link', 'O': 'COMPLIANCE GRADE',
    'P': 'Automatic Fail?', 'Q': 'Noncompliant Categories Count', 'R': 'Application Posted',
    'S': 'Policy Summary Posted (as PDF, or on landing page)', 'T': 'Policy Statement Posted',
    'U': 'Consistent across posted documents (Y/N)',
    'V': 'Primary Service Area boundaries compliant with 2007 guidelines?', 'W': 'No time limit to submit?',
    'X': 'Notes on timeframe', 'Y': 'No evidence of asset checks', 'Z': 'No mention of immigration status as a barrier',
    'AA': 'Inconsistency notes', 'AB': 'Languages Available', 'AC': 'Notes (e.g. use of "charity care")',
    'AD': 'ENTIRE Uniform Application', 'AE': 'Contact information included in application', 'AF': 'Contact phone #',
    'AG': 'Income & Discount Tables Incuded in Application', 'AH': 'FPL Guidelines (current year)',
    'AI': 'Max FPL (compliant is =/>400%)', 'AJ': 'Installments capped at 5% of monthly income',
    'AK': 'Application notes (any prohibited information?)', 'AL': 'Primary Service Area described in summary?',
    'AM': 'Means of applying for assistance explained', 'AN': 'Income levels used to determine assistance',
    'AO': 'Notes', 'AP': 'SEPTEMBER - PDF in Folder', 'AQ': 'Other Notes',
    'AR': 'Previous Grade', 'AS': 'Unverified Columns (manual check)', 'AT': 'Change Notes (latest audit)',
    'AU': 'Sources (latest audit)', 'AV': 'Grade Status', 'AW': 'Fields Changed in Last Update',
    'AX': '# Fields Changed in Last Update', 'AY': 'Grade Changed in Last Update',
    'AZ': 'Last Updated', 'BA': 'Last Checked',
}
LETTERS = list(COLUMNS)
BINARY = ['R', 'S', 'T', 'U', 'V', 'W', 'Y', 'Z', 'AD', 'AE', 'AG', 'AH', 'AJ', 'AL', 'AM', 'AN']
GRADED = BINARY + ['AI']                      # AI holds a multiple of 100% FPL (4 = 400%) or "no" when < 400%
TEXT = ['X', 'AA', 'AB', 'AC', 'AF', 'AK', 'AO', 'AQ']
CSV_FIELDS = ['hospital_id'] + [f'{k} {v}' for k, v in COLUMNS.items()]


def hospital_id(ocn_pfi, name):
    """Same convention as src/seed.py: OCN_PFI, or a deterministic UNRESOLVED id."""
    if ocn_pfi:
        return str(ocn_pfi).strip()
    return 'UNRESOLVED-' + hashlib.sha256(str(name).strip().encode()).hexdigest()[:12]


def config():
    return json.loads(CONFIG.read_text())


def read_tracker():
    with TRACKER.open(newline='', encoding='utf-8') as f:
        rows = []
        for raw in csv.DictReader(f):
            rows.append({'hospital_id': raw['hospital_id'],
                         **{k: raw[f'{k} {v}'] for k, v in COLUMNS.items()}})
        return rows


def write_tracker(rows):
    with TRACKER.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(CSV_FIELDS)
        for r in rows:
            w.writerow([r['hospital_id']] + [r.get(k, '') if r.get(k) is not None else '' for k in LETTERS])


def norm(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip().lower() if str(v).strip().lower() in ('yes', 'no') else str(v).strip()


def grade(row):
    """Mirror of the spreadsheet formulas in O/P/Q (rubric: auto-F for missing application,
    missing/partial Uniform Application, or missing policy statement)."""
    auto_f = any(norm(row.get(c)) == 'no' for c in ('R', 'AD', 'T'))
    n = sum(1 for c in BINARY + ['AI'] if norm(row.get(c)) == 'no')
    if auto_f:
        g = 'F'
    else:
        g = 'A' if n == 0 else 'B' if n <= 3 else 'C' if n <= 6 else 'D' if n <= 9 else 'F'
    return g, auto_f, n
