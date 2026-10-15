# Decisions

## 2026-10-15: sole authorized original-test assertion change

The cohort definition changed to provenance-complete. The old assertion in
`tests/test_public_incident_import.py` tested the legacy 231-row import.
The user explicitly authorized changing only that assertion to compare the
readiness report with the admitted count read from the live cohort manifest.
No new hardcoded count replaces it. All other original test sources remain
unchanged. The frozen baseline hashes are preserved; the integrity validator
reverses exactly this assertion replacement before checking its original hash.

`benchmark/cohort_admission_history.json` records the first authentic publication
count and manifest digest. A new regression test rejects a live count below the
published history. Tests never regenerate the history from the current count.
This is a deliberate exception to the 201-original-tests-untouched requirement
and must be listed as the single modified original test in the final report.
