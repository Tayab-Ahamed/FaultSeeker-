# Reproducibility notes

## 1. Saved benchmark prediction producer

- Run ID: `original-v1-pinned-sequential-20261017`.
- Entrypoint: `scripts/reproduce/run_original_provider_pinned.py`.
- Producer commit: `1b1c7395771663622dd14b9731b4b8b471221960`.
- Variant: `llm-free`.
- Model: `llm-free-function-ranker`.
- Provider policy: BlockPI for Ethereum and BSC; dRPC listed as the spare and not used for that run.
- Saved run manifest: `reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json`.
- The producer call path invokes `ForensicsOrchestrator.run(...)`, then `FunctionRanker().rank(...)` in `scripts/reproduce/run_original_provider_pinned.py`.

Evidence: `scripts/reproduce/run_original_provider_pinned.py`; commit `1b1c7395771663622dd14b9731b4b8b471221960`; `reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json`.

## 2. Commit `70d1b09`

- Commit: `70d1b099c0b1dad524bc89ba4e707ea94b7038b9`.
- Message: `fix: rescore provider-pinned benchmark offline`.
- Scoring-rule change: `benchmark/honest_eval/localization.py::_prediction_keys` accepts `prediction["code_address"]` as an address fallback when `prediction["address"]` is absent.
- Offline application: `scripts/reproduce/finalize_provider_pinned_report.py::rescore_rows` recomputed stored score fields from the saved predictions and ground truth.
- Affected successful rows: 67 of 110.
- Prediction-list hashes for the 67 affected rows: unchanged, 67 of 67.
- Stored fields changed among the affected rows:
  - `first_hit_rank`: 67 rows
  - `recall_at_1`: 25 rows
  - `recall_at_3`: 49 rows
  - `recall_at_5`: 52 rows
  - `target_function_count`: 0 rows
- R@1 using archival ranks at `240fd9f`: 0/110.
- R@1 using current stored ranks after `70d1b09`: 25/110.

Evidence: commit `70d1b099c0b1dad524bc89ba4e707ea94b7038b9`; `reports/new_batches/batchA_adapterfix4/job1_summary.json`; `reports/new_batches/batchA_adapterfix4/job1_70d1_facts.json`; `reports/new_batches/batchA_adapterfix3/scope_audit.json`.

## 3. Replay controls

The four-control gate recorded these results:

| Control | Saved rank | Adapter rank | Saved candidates | Adapter candidates |
| --- | ---: | ---: | ---: | ---: |
| `0x0788...8cceb` | `None` | `None` | 244 | 244 |
| `0x9582...9313c` | 19 | 27 | 100 | 100 |
| `0xa6f6...0b2aa` | 7 | `None` | 7 | 51 |
| `0xc310...b111d` | `None` | 33 | 20 | 55 |

Evidence: `reports/new_batches/batchA_adapterfix/control_report.json`.

The producer-era replay on the three failing controls recorded:

| Control | Saved rank | Producer-era replay rank | Saved candidates | Producer-era replay candidates |
| --- | ---: | ---: | ---: | ---: |
| `0x9582...9313c` | 19 | `None` | 100 | 100 |
| `0xa6f6...0b2aa` | 7 | `None` | 7 | 51 |
| `0xc310...b111d` | `None` | `None` | 20 | 55 |

Evidence: `reports/new_batches/batchA_adapterfix2/original_entrypoint_controls.json`; producer commit `1b1c7395771663622dd14b9731b4b8b471221960`.

For the 3 of 3 rows with replayable local full trace copies, the local replay candidate lists did not reproduce the saved candidate lists. The cause was not established in the recorded replay results.

Evidence: `reports/new_batches/batchA_adapterfix2/original_entrypoint_controls.json`; `reports/new_batches/batchA_adapterfix2/provenance.md`.

## 4. Batch A

- Frozen Batch A canonical SHA-256: `4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21`.
- Frozen valid-set SHA-256: `fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785`.
- Mining outcome: 24 ETH traces were obtained; 16 non-ETH attempts failed with `transaction not found`.
- Valid set: 23 records.
- Diagnostic classifications for the 23 valid records:
  - `adapter_or_format_mismatch`: 21
  - `label_in_trace_but_ranked_low`: 1
  - `label_not_in_trace`: 1

Evidence: `reports/new_batches/batchA_candidates.json`; `reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json`; `reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/manifest.json`; `reports/new_batches/batchA_diagnostic/diagnostic.json`.

No fresh-data metric exists yet because:

- The dRPC fetch stopped at a free-plan/billing/card prompt after partial fetching.
- PublicNode returned `result: null` for the 21 missing receipts after refetch.
- No BlockPI Ethereum endpoint was configured for the original runner inputs.

Evidence: `reports/new_batches/batchA_adapterfix4/fetch_abort.json`; `reports/new_batches/batchA_adapterfix4/receipt_refetch_report.json`; `reports/new_batches/batchA_adapterfix4/job2_final_report.md`; `scripts/reproduce/run_original_provider_pinned.py`; project `.env` configuration check.

The corrected verification gate produced 2 verified rows and 21 excluded rows. The producer-era replay result for the verified sample was:

- Primary address+function: R@1 0/2, R@3 0/2, R@5 0/2.
- Function-only sensitivity: R@1 0/2, R@3 0/2, R@5 0/2.
- Address-only sensitivity: R@1 1/2, R@3 1/2, R@5 1/2.
- Candidate counts: 10 and 32; mean 21.
- Sample size: N=2 — **too small to read**.

Evidence: `reports/new_batches/batchA_adapterfix4/producer_batchA_measurement_final.json`; `reports/new_batches/batchA_adapterfix4/job2_final_report.md`; producer commit `1b1c7395771663622dd14b9731b4b8b471221960`.

## 5. Needed to finish

- An Ethereum node with full transaction and receipt history for the remaining Batch A ETH transactions.
- A single producer-era replay using commit `1b1c7395771663622dd14b9731b4b8b471221960`.
- The verification gate must check transaction hash equality, receipt transaction-hash equality, equal transaction/receipt block numbers, and a non-pending transaction before replay.

Evidence: `reports/new_batches/batchA_adapterfix4/job2_final_verification.json`; `reports/new_batches/batchA_adapterfix4/job2_final_report.md`; `scripts/reproduce/run_original_provider_pinned.py`; commit `1b1c7395771663622dd14b9731b4b8b471221960`.
