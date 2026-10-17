# Strict final claim disposition

This audit covers the 18 paper claims in the current claim-evidence lane and
cross-checks them against `benchmark/claim_registry.py`, the historical claim
closure decisions, retained artifacts, and offline command/test evidence. The
paper files were not edited.

`VERIFIED` is reserved for a paper sentence whose stated scope and endpoint
are actually supported. A valid hash, a populated field, a literal string
count, a saved number, or a generic fixture test does not verify an incident,
annotation, cohort, case study, provider, or paper-scale experiment.

## 18-claim disposition

| # | Strict status | Evidence | Exact safe wording or disposition |
|---:|---|---|---|
| 1 | REWORD | `reports/claim_evidence/summary.json`; `reports/claim_evidence/source_resolution_audit.csv`; `reports/canonical_history/cohort_history.json`; `reports/claim_closure/local_snapshot/claim_report.md` | “The frozen fca6b99 analysis CSV has 231 rows, eight chain strings, syntactically valid transaction-hash fields, and recorded source fields; a free source-resolution probe resolved at least one URL for 161 rows and did not resolve one for 70. These observations do not establish authentic incidents, independent annotations, or a provenance-complete cohort.” Blocker: `claim_report.md` records 231/231 missing ground truth, independent annotation, independent sources, receipt, trace, transaction, and verification evidence for the accepted-data gate. |
| 2 | VERIFIED (local-only) | `reports/canonical_history/PAPER_VS_REPO.md`; `reports/claim_closure/local_snapshot/claim_report.md`; `tests/test_claim_registry.py`; `reports/reproducibility/FINAL_REPORT.md` | “The 201 original test sources are unchanged and the canonical local record reports 201 original tests passed.” This verifies the original local test-scope sentence only; it does not verify the paper’s empirical study. The current fresh-clone/full-suite result is a separate offline check (954 passed, 7 skipped in the retained run). |
| 3 | REWORD | `reports/claim_evidence/chain_shares.csv`; `reports/claim_evidence/summary.json`; `reports/canonical_history/cohort_history.json` | “In the frozen fca6b99 CSV, Ethereum contributes 132/231 rows (57.1429%) and eight chain strings are present.” The paper’s 10-chain/47.6% population claim is contradicted: every fixed CSV version has eight chains; the current version has 183 rows. |
| 4 | REWORD | `reports/claim_evidence/vulnerability_swc_mapping_reviewed.csv`; `reports/claim_evidence/swc_registry_recheck.md` | “The frozen CSV contains 82 distinct vulnerability-label strings; 36 retain an existing SWC classification and 46 are recorded as having no SWC equivalent after a conservative registry-scope review.” This is not proof of 82 semantic vulnerability classes or correct per-incident SWC/DASP annotation. |
| 5 | REWORD | `reports/claim_evidence/class_proportions.csv`; `reports/canonical_history/PAPER_VS_REPO.md` | “The frozen CSV stores Simple 19/231 (8.2251%), Moderate 62/231 (26.8398%), Complex 91/231 (39.3939%), and Exceptionally Complex 59/231 (25.5411%).” The paper’s 6.5/33.3/32.5/27.6 percentages are contradicted; trace-verified function-count bins for an authentic paper cohort are absent. |
| 6 | REWORD | `reports/claim_evidence/reentrancy_rows.csv`; `reports/claim_evidence/reentrancy_replay_verification.csv`; `reports/canonical_history/PAPER_VS_REPO.md` | “Seventeen frozen rows carry a reentrancy label string.” Two rows have retained trace artifacts and 15 do not; none is independently verified as a reentrant incident because trace presence alone is not adjudication. |
| 7 | UNVERIFIABLE | `reports/canonical_history/PAPER_VS_REPO.md`; `reports/claim_closure/claims/13.json`; `reports/research_results/research_tables.tex`; `reports/claim_evidence/table_v_saved_results.csv` | Remove the paper’s Table V/SSTORE precision, recall, F1, and detector-gain sentence. The retained artifact is a different saved feature-harness aggregate (FaultSeeker++ F1=0.7586 on 1,231 rows, TP=154, FP=21, TN=979, FN=77); it is not the paper’s SSTORE detector result. |
| 8 | UNVERIFIABLE | `reports/honest_results/baseline_comparison.csv`; `reports/canonical_history/reruns/8e02f92c639eb3983c536501f093a323b2157ff5/status.json`; `reports/research_results/research_tables.tex`; `reports/honest_results/adversarial_robustness.csv` | “Saved local proxy aggregates exist, but the paper’s baseline/ablation and adversarial-retention experiment is not reproduced.” The offline rerun reports full F1=0.7586 and -TIG F1=0.6531, while the saved -TIG row is 0.6565. The CSV’s five proxy perturbations are not proof of the paper’s retained N=250 experiment. |
| 9 | REWORD | `reports/claim_evidence/source_resolution_audit.csv`; `reports/claim_evidence/cohort_provenance_gaps.csv`; `reports/canonical_history/cohort_history.json` | “Each frozen row has a syntactically valid hash field and a recorded source URL field; 70 recorded URLs were unresolved by the free probe.” Field presence does not establish that the transaction occurred, that the label is correct, or that two independent sources/annotators support it. |
| 10 | REWORD | `reports/claim_evidence/chain_capability_matrix_final.csv`; `reports/claim_evidence/chain_capability_matrix.csv`; `reports/claim_closure/rpc_capability_conclusion.json` | “A chain/provider is counted as trace-capable only after a successful required historical trace response.” The retained eight-chain free-endpoint probe produced zero usable `debug_traceTransaction` responses; one configured Ethereum observation is not universal provider or chain support. |
| 11 | REWORD | `reports/claim_evidence/measured_cost_run.json`; `reports/claim_evidence/measured_cost_run_state.json`; `reports/claim_evidence/cost_zero_spend_proof.json`; `reports/canonical_history/PAPER_VS_REPO.md`; `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json` | “No measured cost result was obtained: N=100 completed 0 because the tracked repository has no preregistered selection manifest with 100 unique transaction IDs and a 50/30/20 workload-tier binding; the extension was not started. Under retained assumptions only, hybrid cost is modeled at $0.039/query versus $0.060/query for cloud-only, a 35.0% modeled reduction.” No dotenv was loaded, no provider key was used, and no API/model call was made. |
| 12 | REWORD | `reports/provenance_hunt/experiments/measurement_frontier.json`; `reports/claim_closure/claims/3.json`; `reports/claim_closure/claims/18.json` | “Future work should obtain an independently reviewed cohort, paired usage/quality measurements, observed provider coverage, and retained confidence vectors before making the corresponding empirical claims.” The limitation/future-work sentence is not an empirical result. |
| 13 | REWORD | `reports/claim_evidence/localization_summary.json`; `reports/honest_results/localization_metrics.json`; `reports/canonical_history/PAPER_VS_REPO.md` | “The retained localization summary records 7 top-1 hits among 115 evaluated targets (6.09%, rounded to 6.1%) with MRR=0.173 under the function-match protocol.” This is a recorded historical aggregate, not an independently re-run paper result: raw ranked predictions are unavailable and the 115-target denominator includes a duplicate transaction. |
| 14 | REWORD | `reports/claim_evidence/chain_capability_matrix_final.csv`; `reports/claim_closure/rpc_capability_conclusion.json` | “The retained eight-chain probe completed one observation per listed endpoint; no endpoint returned a usable historical `debug_traceTransaction` result.” Do not state that all eight chains have verified free RPC capability. |
| 15 | DROP | `reports/claim_closure/claims/15.json`; `reports/canonical_history/PAPER_VS_REPO.md` | Remove the Compound/cToken case-study sentence. The recovered narrative has no exact transaction hash, trace, or source linkage for the legitimate recursive control, so the case cannot be independently identified. |
| 16 | DROP | `reports/claim_closure/claims/28.json`; `reports/provenance_hunt/experiments/measurement_frontier.json`; `tests/test_table_vi.py` | Remove all Table VI PMS/CES/TCS/LCS category averages. The test is an aggregator contract using local/synthetic rows; no production per-function score vectors or declared paper-cohort averaging are retained. |
| 17 | DROP | `reports/claim_closure/claims/29.json`; `reports/provenance_hunt/experiments/guidance.json`; `reports/canonical_history/PAPER_VS_REPO.md` | Remove the “20 randomly selected cases, 68% to 81%” guidance sentence. The retained guidance experiment is `BLOCKED-BY-DATA` with zero accepted rows; no selection policy, paired rankings, or quality aggregation exists. |
| 18 | VERIFIED (workflow-only) | `scripts/reproduce/run_all.py`; `scripts/reproduce/claim_evidence.py`; `reports/reproducibility/FINAL_REPORT.md`; `REPRODUCING.md` | “The retained offline reproduction and claim-evidence commands run without paid APIs or model-provider calls.” This verifies the local workflow, not the unsupported paper-scale metrics, annotations, or provider claims. |

## Strict run outputs

The retained local headline run reports:

```text
honest_f1                  0.7586  (saved feature-harness aggregate)
modeled_cost_saving_pct   35.0    (assumption-based arithmetic)
localization_top1_pct      6.1    (recorded 7/115 function-match summary)
reentrancy_label_count    17      (label-string count)
vulnerability_label_count 82      (distinct exact strings)
cohort_rows               231     (frozen CSV row count)
chain_count                 8     (frozen CSV distinct-value count)
```

These outputs are descriptive and scope-limited. They do not promote the
paper’s incident, annotation, case-study, all-chain, Table IV/V/VI, cost,
retention, or guidance claims.

## New original-benchmark measurement

The imported upstream ASE 2025 benchmark was measured separately under
`benchmark/protocols/original_benchmark_function_localization_v1.md`.
The LLM-free FunctionRanker/orchestrator run covered all 115 input files:

```text
n_total=115
n_ok=2
n_failed=113
Recall@1=0.000000
Recall@3=0.000000
Recall@5=0.000000
actual_cost_usd=0.000000
```

Raw outputs are under
`reports/original_benchmark/llm-free/original-v1-seed20261017/raw/` and the
manifest is
`reports/original_benchmark/llm-free/original-v1-seed20261017/manifest.json`.
The two successful deterministic runs did not hit their function-level
targets. The 113 failed cases were retained in the denominator; public RPC
trace acquisition returned authentication/no-trace/missing-trie failures and
bounded timeouts. This is a new measurement on the original benchmark, not a
reproduction of the paper's Table II values. No API-backed model measurement
was dispatched; see the separate `api_run_status.json` blocker record.
