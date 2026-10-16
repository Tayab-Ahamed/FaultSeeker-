# Final Claim Disposition

This is the post-run disposition of the 18 NMITCON paper claims. The paper
file is intentionally unchanged. `VERIFIED` means only the scoped statement
shown here is supported by a retained local artifact or a reproducible offline
calculation; it does not promote the original paper-scale claim when the
underlying population or protocol differs.

| # | Final status | Evidence | Exact final wording / disposition |
|---:|---|---|---|
| 1 | REWORD | `reports/claim_evidence/summary.json`; `reports/canonical_history/cohort_history.json`; `reports/canonical_history/PAPER_VS_REPO.md` | “The frozen fca6b99 analysis CSV contains 231 rows across eight chains; each retained row has a syntactically valid transaction hash and a recorded source URL. The repository also contains a later 183-row cohort, and these counts do not independently establish annotation authenticity.” |
| 2 | REWORD | `scripts/reproduce/run_all.py`; `reports/reproducibility/FINAL_REPORT.md`; `tests/test_train_probe_integration.py` | “The offline headline reproduction passes and the gzip-immutable integration test compares decompressed content; this verifies local arithmetic and artifact integrity, not that the original 201-test paper evaluation was reproduced.” |
| 3 | VERIFIED | `reports/claim_evidence/chain_shares.csv`; `reports/claim_evidence/summary.json` | “In the frozen 231-row analysis CSV, Ethereum contributes 132/231 rows (57.1429%) and the cohort contains eight chain strings.” |
| 4 | REWORD | `reports/claim_evidence/vulnerability_swc_mapping_reviewed.csv`; `reports/claim_evidence/swc_mapping_summary.md` | “The frozen cohort contains 82 distinct vulnerability-label strings; 36 preserve an existing SWC classification and 46 are conservatively recorded as `no SWC equivalent` with confidence and reasons. No new SWC ID was assigned without a clear fit.” |
| 5 | REWORD | `reports/claim_evidence/class_proportions.csv`; `reports/canonical_history/PAPER_VS_REPO.md` | “The frozen CSV stores Simple 19/231 (8.2251%), Moderate 62/231 (26.8398%), Complex 91/231 (39.3939%), and Exceptionally Complex 59/231 (25.5411%); these are stored-label proportions, not independently trace-adjudicated paper proportions.” |
| 6 | REWORD | `reports/claim_evidence/reentrancy_rows.csv`; `reports/claim_evidence/summary.json` | “Seventeen frozen rows contain a reentrancy label string; this is a label-string count, not an independently adjudicated count of reentrant incidents.” |
| 7 | VERIFIED | `reports/claim_evidence/table_v_saved_results.csv`; `reports/canonical_history/reruns/8e02f92c639eb3983c536501f093a323b2157ff5/status.json` | “The saved local feature-harness aggregate reports F1=0.7586 on 1,231 represented rows (TP=154, FP=21, TN=979, FN=77).” |
| 8 | REWORD | `reports/honest_results/baseline_comparison.csv`; `reports/canonical_history/reruns/8e02f92c639eb3983c536501f093a323b2157ff5/status.json`; `reports/research_results/research_tables.tex`; `reports/honest_results/adversarial_robustness.csv` | “Saved local proxy aggregates and an offline rerun exist, but the paper’s Table IV ablation and adversarial-retention numbers are not reproduced: the rerun reports F1=0.7586 for the full system and -TIG F1=0.6531, while the saved -TIG row is 0.6565. The adversarial CSV is a saved proxy table, not proof of the paper’s retained N=250 experiment.” |
| 9 | REWORD | `reports/claim_evidence/cohort_provenance_gaps.csv`; `reports/claim_evidence/summary.json` | “Every retained frozen row has a syntactically valid transaction hash and at least one recorded source URL; field presence alone does not prove that the transaction or label was independently authenticated.” |
| 10 | REWORD | `reports/claim_evidence/chain_capability_matrix.csv`; `reports/claim_closure/rpc_capabilities.json`; `reports/claim_closure/rpc_capability_conclusion.json` | “A provider is counted as supported only when it successfully returns the required trace data; the retained evidence establishes a configured Ethereum call-trace observation but does not establish universal provider or chain support.” |
| 11 | REWORD | `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json`; `scripts/reproduce/modeled_cost.py`; `reports/canonical_history/PAPER_VS_REPO.md` | “Under the stated tier-mixture assumptions, hybrid cost is $0.039/query versus $0.060/query for cloud-only, implying a 35.0% modeled reduction; this is not an observed 60–80% saving, invoice, or paired 100-transaction result.” |
| 12 | REWORD | `reports/claim_evidence/CLAIMS_FINAL.md`; `reports/provenance_hunt/experiments/measurement_frontier.json` | “Future work should obtain an independently annotated cohort, paired usage and quality measurements, observed provider coverage, and retained production confidence vectors before making the corresponding empirical claims.” |
| 13 | VERIFIED | `reports/claim_evidence/localization_summary.json`; `reports/honest_results/localization_metrics.json` | “The saved function-match localization artifact records 7 top-1 hits among 115 evaluated transactions (6.1%), with MRR=0.173.” |
| 14 | REWORD | `reports/claim_evidence/chain_capability_matrix.csv`; `reports/claim_closure/rpc_capability_conclusion.json` | “Universal free-RPC trace capability is not established for the eight-chain frozen cohort; untested or unsupported endpoints remain unknown and are not counted as capability.” |
| 15 | DROP | `reports/provenance_hunt/experiments/waf.json`; `reports/claim_closure/claims/27.json` | **Remove the WAF percentage/security-result claim.** The retained record is `PENDING-CREDENTIALS`, with `execution_requested=false` and `requests_dispatched=0`; no WAF case corpus or execution artifact exists. |
| 16 | DROP | `reports/provenance_hunt/experiments/measurement_frontier.json`; `reports/claim_closure/claims/28.json`; `tests/test_table_vi.py` | **Remove the Table VI category-average claim.** The local test validates only an aggregator contract with synthetic/local rows; no production PMS/CES/TCS/LCS vectors for the paper cohort are retained. |
| 17 | DROP | `reports/provenance_hunt/experiments/guidance.json`; `reports/canonical_history/previous_decisions/29.json` | **Remove the 20-transaction improvement claim.** The retained guidance experiment is `BLOCKED-BY-DATA` with `accepted_rows=0`; no paired 20-transaction selection, ranking output, or quality aggregation exists. |
| 18 | REWORD | `DEMO.md`; `REPRODUCING.md`; clean-clone rehearsal log; `scripts/reproduce/run_all.py` | “The current working tree can run offline arithmetic and artifact checks without model or paid-provider calls; a clean Git clone cannot execute the documented commands until `.venv` and the six helper scripts plus `reports/reproducibility/FINAL_REPORT.md` are provisioned.” |

## Settled open items

| Open item | Settlement |
|---|---|
| 60–80% cost claim | Not made true. The retained arithmetic is 35.0% modeled overall; 58.3333% is only the Tier-2 sub-mixture arithmetic. |
| Table IV ablation and adversarial retention | Not made true as paper claims. The offline feature-harness rerun is retained, but it reports 0.7586 full-system F1 and -TIG 0.6531; the saved -TIG row is 0.6565. The adversarial CSV is a proxy artifact, not a retained N=250 study. |
| 183 vs 231 rows | Both are real repository versions. Use the frozen fca6b99 CSV only when explicitly saying “231-row frozen analysis CSV”; do not call it the sole or fully authenticated cohort because the later cohort has 183 rows and provenance acceptance remains incomplete. |
| SWC mapping | Settled conservatively: 36 existing mappings preserved; all 46 previously unmapped strings are `no SWC equivalent` with confidence and one-line reasons. |
| Clean-clone reproducibility | Not fully true. The clean clone lacks `.venv/bin/python` and the earlier helper scripts/report. Documentation now states the prerequisite; no dependency installation or hidden setup was performed. |

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
