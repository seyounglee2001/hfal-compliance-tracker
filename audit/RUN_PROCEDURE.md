# Scheduled audit run: step by step

The scheduled agent follows this file on every run. Each run re-checks the health systems that were checked least recently (`systems_per_run` in `config.json`, default 10). With 71 systems, that covers the whole state in about 7–8 runs.

1. **Get the repo.** Clone `seyounglee2001/hfal-compliance-tracker` (shallow is fine) and `cd` into it. `pip install openpyxl` if it's missing.
2. **Pick the batch.** `python audit/scripts/select_batch.py`. This writes `audit/work/batch.json`. To audit specific systems instead: `--system "Northwell Health" --system "Kaleida Health"`.
3. **Audit.** Follow `audit/AUDIT_INSTRUCTIONS.md` for every hospital in the batch and write `audit/work/results.json`. Parallel helper agents are fine: one per 2–3 systems, each writing its own file, then merge them into one list.
4. **Self-check before applying.**
   - Every `hospital_id` in the batch is present exactly once.
   - Every "no" that differs from the recorded value has evidence quoted in a text column or in `changes_vs_previous`.
   - Spot-check two changed findings by re-reading the source.
5. **Apply.** `python audit/scripts/apply_results.py audit/work/results.json`. It refuses malformed results. It updates `tracker.csv`, appends `changelog.csv`, saves the raw findings to `audit/runs/<run_id>.json`, and writes `audit/work/summary.md`.
6. **Rebuild the spreadsheet.** `python audit/scripts/build_xlsx.py`.
7. **Commit and push.**
   ```bash
   git add audit/tracker.csv audit/changelog.csv audit/runs audit/exports
   git commit -F audit/work/summary.md     # add the session attribution lines the environment specifies
   git fetch origin main && git rebase origin/main && git push origin HEAD:main
   ```
   If the push is refused, don't retry in a loop. Report it, and keep the summary in the final message.
8. **Report.** End with the summary: hospitals checked, grades changed, and anything left unverified.

Never edit `tracker.csv` or the spreadsheet by hand. All changes go through `apply_results.py`, so every change lands in `changelog.csv` and in git history.
