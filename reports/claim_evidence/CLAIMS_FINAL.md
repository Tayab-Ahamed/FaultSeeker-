# Final Claim Disposition

This is the post-run disposition of the 18 NMITCON paper claims. The paper
file is intentionally unchanged. `VERIFIED` means only the scoped statement
shown here is supported by a retained local artifact or a reproducible offline
calculation; it does not promote the original paper-scale claim when the
underlying population or protocol differs.

| # | Final status | Evidence | Exact final wording / disposition |
|---:|---|---|---|
| 1 | VERIFIED | `reports/claim_evidence/source_resolution_audit.csv`; `reports/canonical_history/cohort_history.json` | “The frozen fca6b99 CSV contains 231 rows with 0 invalid hash fields; the free source-resolution probe resolved at least one recorded URL for 161 rows and did not resolve one for 70 rows. These results do not establish annotation authenticity.” |
| 2 | VERIFIED | `scripts/reproduce/run_all.py`; `reports/reproducibility/FINAL_REPORT.md`; `tests/test_train_probe_integration.py` | “The offline headline reproduction passes, the decompressed-content gzip test passes, and a fresh configured clone passes 954 tests with 7 skips; this is not a reproduction of the original 201-test paper study.” |
| 3 | VERIFIED | `reports/claim_evidence/chain_shares.csv`; `reports/claim_evidence/summary.json` | “In the frozen 231-row analysis CSV, Ethereum contributes 132/231 rows (57.1429%) and the cohort contains eight chain strings.” |
| 4 | VERIFIED | `reports/claim_evidence/vulnerability_swc_mapping_reviewed.csv`; `reports/claim_evidence/swc_registry_recheck.md` | “The frozen cohort contains 82 distinct vulnerability-label strings; 36 preserve an existing SWC classification and 46 are recorded as `no SWC equivalent` after a second registry-scope review, with confidence and reasons.” |
| 5 | VERIFIED | `reports/claim_evidence/class_proportions.csv` | “The frozen CSV stores Simple 19/231 (8.2251%), Moderate 62/231 (26.8398%), Complex 91/231 (39.3939%), and Exceptionally Complex 59/231 (25.5411%).” |
| 6 | VERIFIED | `reports/claim_evidence/reentrancy_replay_verification.csv`; `reports/claim_evidence/reentrancy_rows.csv` | “Seventeen frozen rows contain a reentrancy label string; no independently verified reentrant incident was established from the retained local trace evidence because all 17 rows lacked a saved call-trace replay artifact.” |
| 7 | VERIFIED | `reports/claim_evidence/table_v_saved_results.csv`; `reports/canonical_history/reruns/8e02f92c639eb3983c536501f093a323b2157ff5/status.json` | “The saved local feature-harness aggregate reports F1=0.7586 on 1,231 represented rows (TP=154, FP=21, TN=979, FN=77).” |
| 8 | REWORD | `reports/honest_results/baseline_comparison.csv`; `reports/canonical_history/reruns/8e02f92c639eb3983c536501f093a323b2157ff5/status.json`; `reports/research_results/research_tables.tex`; `reports/honest_results/adversarial_robustness.csv` | “Saved local proxy aggregates and an offline rerun exist, but the paper’s Table IV ablation and adversarial-retention numbers are not reproduced: the rerun reports F1=0.7586 for the full system and -TIG F1=0.6531, while the saved -TIG row is 0.6565. The adversarial CSV is a saved proxy table, not proof of the paper’s retained N=250 experiment.” |
| 9 | VERIFIED | `reports/claim_evidence/source_resolution_audit.csv` | “All 231 frozen rows have syntactically valid transaction hashes; a free source-resolution probe resolved at least one recorded URL for 161 rows and left 70 rows unresolved, so source-field presence is not presented as independent authentication.” |
| 10 | REWORD | `reports/claim_evidence/chain_capability_matrix.csv`; `reports/claim_closure/rpc_capabilities.json`; `reports/claim_closure/rpc_capability_conclusion.json` | “A provider is counted as supported only when it successfully returns the required trace data; the retained evidence establishes a configured Ethereum call-trace observation but does not establish universal provider or chain support.” |
| 11 | REWORD | `reports/claim_evidence/cost_local_model_check.txt`; `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json`; `scripts/reproduce/modeled_cost.py` | “No local Ollama executable/model was available, so no 100-transaction 5:3:2 local-model workload was dispatched. Under the retained assumptions, hybrid cost is $0.039/query versus $0.060/query for cloud-only, a 35.0% modeled reduction rather than a measured saving.” |
| 12 | REWORD | `reports/claim_evidence/CLAIMS_FINAL.md`; `reports/provenance_hunt/experiments/measurement_frontier.json` | “Future work should obtain an independently annotated cohort, paired usage and quality measurements, observed provider coverage, and retained production confidence vectors before making the corresponding empirical claims.” |
| 13 | VERIFIED | `reports/claim_evidence/localization_summary.json`; `reports/honest_results/localization_metrics.json` | “The saved function-match localization artifact records 7 top-1 hits among 115 evaluated transactions (6.1%), with MRR=0.173.” |
| 14 | REWORD | `reports/claim_evidence/chain_capability_matrix_final.csv`; `reports/claim_closure/rpc_capability_conclusion.json` | “The eight-chain free-endpoint probe completed one row per chain: no endpoint produced a usable historical `debug_traceTransaction` result. A provider is counted as trace-capable only after a successful required trace response; unsupported or empty responses remain unsupported.” |
| 15 | DROP | `reports/provenance_hunt/experiments/waf.json`; `reports/claim_closure/claims/27.json` | **Remove the WAF percentage/security-result claim.** The retained record is `PENDING-CREDENTIALS`, with `execution_requested=false` and `requests_dispatched=0`; no WAF case corpus or execution artifact exists. |
| 16 | DROP | `reports/provenance_hunt/experiments/measurement_frontier.json`; `reports/claim_closure/claims/28.json`; `tests/test_table_vi.py` | **Remove the Table VI category-average claim.** The local test validates only an aggregator contract with synthetic/local rows; no production PMS/CES/TCS/LCS vectors for the paper cohort are retained. |
| 17 | DROP | `reports/provenance_hunt/experiments/guidance.json`; `reports/canonical_history/previous_decisions/29.json` | **Remove the 20-transaction improvement claim.** The retained guidance experiment is `BLOCKED-BY-DATA` with `accepted_rows=0`; no paired 20-transaction selection, ranking output, or quality aggregation exists. |
| 18 | REWORD | `DEMO.md`; `REPRODUCING.md`; `scripts/reproduce/run_all.py`; fresh-clone rehearsal log | “A fresh Windows Git-Bash clone with `core.autocrlf=false`, Python 3.11.9, the documented requirements install, offline reproduction, full pytest, and the offline ETH no-LLM demo passes; a POSIX-specific venv path was not exercised on this Windows host.” |

## Settled open items

| Open item | Settlement |
|---|---|
| 60–80% cost claim | Not made true. The retained arithmetic is 35.0% modeled overall; 58.3333% is only the Tier-2 sub-mixture arithmetic. |
| Table IV ablation and adversarial retention | Not made true as paper claims. The offline feature-harness rerun is retained, but it reports 0.7586 full-system F1 and -TIG 0.6531; the saved -TIG row is 0.6565. The adversarial CSV is a proxy artifact, not a retained N=250 study. |
| 183 vs 231 rows | Both are real repository versions. Use the frozen fca6b99 CSV only when explicitly saying “231-row frozen analysis CSV”; do not call it the sole or fully authenticated cohort because the later cohort has 183 rows and provenance acceptance remains incomplete. |
| SWC mapping | Settled conservatively after the second registry-scope review: 36 existing mappings preserved; all 46 previously unmapped strings remain `no SWC equivalent` with confidence and one-line reasons. |
| Clean-clone reproducibility | The Windows Git-Bash clean clone now passes setup, offline reproduction, claim evidence generation, 954 tests/7 skips, and the offline ETH demo. A POSIX-specific venv path was not exercised on this Windows host. |

## Local run evidence

The local headline runner completed without network or model calls:

```text
Metric                    | Expected | Reproduced | Result
--------------------------+----------+------------+-------
honest_f1                 | 0.7586   | 0.7586     | PASS
modeled_cost_saving_pct   | 35.0     | 35.0       | PASS
localization_top1_pct     | 6.1      | 6.1        | PASS
reentrancy_label_count    | 17       | 17         | PASS
vulnerability_label_count | 82       | 82         | PASS
cohort_rows               | 231      | 231        | PASS
chain_count               | 8        | 8          | PASS
```

The gzip integration regression test also passes:

```text
1 passed in 5.74s
```

The additional local-only probes reported:

```text
source rows=231 urls=282 unresolved_rows=70 invalid_hashes=0
free RPC capability rows=8; usable historical trace responses=0
local Ollama executable: unavailable (command not found)
```
