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

## 2026-10-16: candidate hash boundaries and per-transaction chain identity

Real cached Sushi source contained longer encoded routes whose first64 hex digits were mistakenly imported as transaction hashes. The GitHub and public incident importers now reject embedded/overlong identifier fragments. GitHub imports resolve each hash through exact explorer-host transaction URLs, retain separately linked chains, and keep unlinked hashes unresolved in explicitly mixed-chain files. This also avoids Optimism/Ethereum hostname shadowing and recognizes observed Phalcon chain paths.

The public incident normalizer scans decoded nested strings, avoiding JSON-escaped newline/tab/CR/Unicode separators dropping valid hashes. Ten new software regression cases were observed failing before their respective fixes, then passed; their fixtures are software checks only and never empirical claim evidence. The registry diagnostic uses only actual SHA-bound cached source bytes and direct production token/URL processing. No legacy CSV, admitted manifest or frozen evaluation split is rewritten, and exact-width candidate hashes still require full provenance/RPC admission.
