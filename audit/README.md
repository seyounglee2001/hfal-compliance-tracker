# HFAL audit layer (agent-maintained, version-controlled)

A version-controlled copy of the CSSNY Hospital Financial Assistance compliance tracker. A scheduled Claude agent keeps it current: each run re-checks the hospitals checked least recently, grades them against the 17-criterion rubric, and commits whatever changed. This folder is separate from the Python app in the repo root (`src/`, SQLite, Streamlit) and doesn't touch it.

## Files
| Path | What it is |
|---|---|
| `tracker.csv` | **Source of truth.** One row per hospital (keyed by `OCN_PFI`), every spreadsheet column, plus **Last Updated** and **Last Checked** |
| `changelog.csv` | Append-only log of every graded-field change: date, run, hospital, field, old value, new value, note |
| `runs/<run_id>.json` | Raw findings and evidence from each run |
| `exports/hfal-compliance-tracker.xlsx` | The spreadsheet, regenerated from `tracker.csv` after every run |
| `config.json` | Current FPL year and table, and how many systems each run covers |
| `AUDIT_INSTRUCTIONS.md` | Grading rules the agent follows |
| `RUN_PROCEDURE.md` | Step-by-step for each scheduled run |
| `scripts/` | `select_batch.py` → (agent audits) → `apply_results.py` → `build_xlsx.py` |

## Dates
- **Last Updated:** the last date any graded field for that hospital changed. It moves only when the data changes.
- **Last Checked:** the last date the agent re-checked that hospital, whether or not anything changed.

## Version history
- Every run is one git commit. The commit message lists each hospital that changed, its grade movement and the fields involved.
- `git log -p audit/tracker.csv` shows every change over time. `changelog.csv` gives the same history as a filterable table.
- To undo a run, `git revert <commit>`.

## Spreadsheet highlights
- **Yellow:** the field changed in that hospital's last update. A cell comment shows the previous value.
- **Grey:** couldn't be verified at the last check, so it's left blank. A cell comment shows the last recorded value.
- **"Grade Status":** marks rows with blanks as *Provisional*, because blanks aren't counted as non-compliant.

## Grading conventions
- Max FPL below 400% is stored as "no", so the count formula catches it.
- The automatic F covers a missing application, an incomplete Uniform Application, or a missing policy statement.
- Column AH checks the FPL year in `config.json`. Update it each January when HHS publishes new guidelines.

## Baseline
Seeded from the November 9, 2026 re-audit of all 212 hospitals. Its comparison against the September 2025 CSSNY grades is recorded in `changelog.csv` under run `2026-11-09-initial`.
