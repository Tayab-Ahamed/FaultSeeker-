# Batch A adapter fix 4

## Job 1 — `70d1b09` facts

- Commit: `70d1b099c0b1dad524bc89ba4e707ea94b7038b9`
- Parent/archive: `240fd9fae9cb56a96f45f37d21a90cf094abc467`
- Message: `fix: rescore provider-pinned benchmark offline`
- Diff summary: 76 files changed, 1,135 insertions, 444 deletions.
- Affected successful benchmark rows: 67.
- Prediction-list hashes unchanged for affected rows: 67/67.
- Changed stored score fields across those rows:
  - `first_hit_rank`: 67 rows
  - `recall_at_1`: 25 rows
  - `recall_at_3`: 49 rows
  - `recall_at_5`: 52 rows
  - `target_function_count`: 0 rows

The scoring-rule change was in `benchmark/honest_eval/localization.py`, in `_prediction_keys`: `prediction["code_address"]` became an address fallback when `prediction["address"]` is absent. `scripts/reproduce/finalize_provider_pinned_report.py::rescore_rows` applied that rule offline to saved predictions and rewrote the stored score fields. The prediction lists themselves were not regenerated.

The saved prediction lists came from `scripts/reproduce/run_original_provider_pinned.py`, run ID `original-v1-pinned-sequential-20261017`, producer-era commit `1b1c7395771663622dd14b9731b4b8b471221960`.

Complete row-level hashes and ranks are in `job1_70d1_facts.json`.

## Job 2 — Batch A

The frozen valid set was checked first: 23 records, all ETH, with the required callTracer fields. The two requested read-only methods were used at approximately 2 requests/second:

- `eth_getTransactionByHash`
- `eth_getTransactionReceipt`

Five raw responses were saved before dRPC returned a paid-plan/billing/card prompt. The fetch stopped immediately. Two transactions have complete transaction/receipt pairs; the third has only its transaction response. The remaining 20 transactions were not fetched.

The producer-era replay and its one scoring run were **not executed** because fetching was required first and the paid-plan prompt required an immediate stop.

Raw responses are under:

```text
reports/new_batches/batchA_adapterfix4/rpc_raw/eth/
```

No API key was printed or saved. The frozen valid set and Batch A artifact were not modified.
