"""Pick the next health systems to re-audit: the ones checked least recently.
Usage: python audit/scripts/select_batch.py [--systems N] [--system "Name" ...]
Writes audit/work/batch.json (git-ignored) and prints a short summary."""
import argparse, json
from collections import OrderedDict
from lib import AUDIT, read_tracker, config, GRADED, TEXT

ap = argparse.ArgumentParser()
ap.add_argument('--systems', type=int, default=None)
ap.add_argument('--system', action='append', help='audit these systems instead of the rotation')
a = ap.parse_args()

rows = read_tracker()
by_sys = OrderedDict()
for r in rows:
    by_sys.setdefault(r['M'], []).append(r)

if a.system:
    chosen = [s for s in by_sys if s in a.system]
else:
    n = a.systems or config()['systems_per_run']
    # oldest "Last Checked" first; ties broken by most unverified cells, then name
    def key(s):
        hs = by_sys[s]
        return (min(h['BA'] or '0000' for h in hs),
                -sum(len([c for c in h['AS'].split(', ') if c and c != 'None']) for h in hs), s)
    chosen = sorted(by_sys, key=key)[:n]

batch = [{'system': s, 'hospitals': [
    {'hospital_id': h['hospital_id'], 'hospital': h['A'], 'city': h['D'], 'zip': h['G'], 'hfa_link': h['N'],
     'last_checked': h['BA'], 'last_updated': h['AZ'],
     'current': {c: h[c] for c in GRADED + TEXT + ['AS', 'AU']}} for h in by_sys[s]]} for s in chosen]
(AUDIT / 'work').mkdir(exist_ok=True)
(AUDIT / 'work' / 'batch.json').write_text(json.dumps(batch, indent=1))
for b in batch:
    print(f"{b['system']}: {len(b['hospitals'])} hospitals, last checked {min(h['last_checked'] for h in b['hospitals'])}")
print(f"{sum(len(b['hospitals']) for b in batch)} hospitals in {len(batch)} systems -> audit/work/batch.json")
