# 18-Claim Evidence Status

This review uses the numbering and scope requested for the current paper audit.
It is deliberately separate from the historical 31-claim registry in
`reports/claim_closure/claims/`, whose numbering is different.

Status meanings:

- **VERIFIED** — the exact scoped statement is reproduced by a frozen local
  artifact or an offline test.
- **REWORD** — the underlying artifact is useful, but the paper wording is too
  broad, ambiguous, or stronger than the evidence.
- **DROP** — no retained evidence supports the claim and it should be removed,
  not softened into an empirical result.

| # | Claim under review | Status | Evidence / replacement wording |
|---:|---|---|---|
| 1 | The evaluated cohort contains 231 authentic, provenance-backed rows. | **REWORD** | `reports/claim_evidence/summary.json` and `cohort_provenance_gaps.csv` verify 231 frozen rows, 8 chains, valid-looking transaction hashes, and a source URL in every row. This does not independently prove that every annotation is authentic. **Use:** “The frozen analysis cohort contains 231 rows; every retained row has a syntactically valid transaction hash and at least one recorded source URL.” |
| 2 | The original test/reproduction suite passes. | **REWORD** | `scripts/reproduce/run_all.py` reproduces the seven requested headline checks. The current full suite is not green: 960 passed, 1 failed, 7 skipped; the failure is immutable gzip-header serialization drift. **Use:** “The offline headline reproduction passes; the full suite has one environment-specific immutable-capture failure.” |
| 3 | Chain composition and Ethereum share are reported correctly. | **VERIFIED** | `reports/claim_evidence/chain_shares.csv`: 231 rows across 8 chains; Ethereum is 132/231 = 57.1429% (57.1% rounded). |
| 4 | The 82 vulnerability labels are mapped to SWC registry classes. | **REWORD** | `vulnerability_swc_mapping.csv` contains all 82 distinct label strings, but only 36 have an existing non-empty SWC field and 46 are unmapped in the frozen CSV. **Use:** “The cohort contains 82 distinct vulnerability label strings; 36 carry an existing SWC classification and 46 do not.” |
| 5 | Complexity classes have the stated proportions. | **VERIFIED** | `reports/claim_evidence/class_proportions.csv`: Simple 19/231 = 8.2251%, Moderate 62/231 = 26.8398%, Complex 91/231 = 39.3939%, Exceptionally Complex 59/231 = 25.5411%. |
| 6 | There are 17 reentrant incidents. | **REWORD** | `reports/claim_evidence/reentrancy_rows.csv` identifies 17 rows whose stored `vuln_type` contains “reentran”. This is a label-string count, not an independently re-annotated incident count. **Use:** “Seventeen frozen rows carry a reentrancy label string.” |
| 7 | Table V reports F1 = 0.7586 for FaultSeeker++. | **VERIFIED** | `reports/claim_evidence/table_v_saved_results.csv` preserves the saved aggregate: n=1231, TP=154, FP=21, TN=979, FN=77, F1=0.7586. Scope it to the saved feature-harness aggregate; do not call it a fresh full-paper replication. |
| 8 | The Table V baselines were run and are comparable. | **REWORD** | The saved baseline artifact contains Static proxy (0.4808), Dynamic trace-rule (0.3733), LLM-only (0.6120), FaultSeeker++ (0.7586), -FAEGL (0.7556), -TIG graph (0.6565), -Learned calib (0.6889), and -LLM routing (0.7586). **Use:** “Saved feature-harness aggregates include the listed baseline rows”; avoid claiming a newly rerun or independently audited comparison. |
| 9 | All cohort entries represent real transactions and labels. | **REWORD** | `cohort_provenance_gaps.csv` shows no missing hash/URL fields, but field presence does not establish annotation authenticity. **Use:** “Each retained row includes a syntactically valid transaction hash and recorded source URL; any synthetic or unverified label must be identified explicitly.” |
| 10 | The system supports all named providers/chains. | **REWORD** | `chain_capability_matrix.csv` records free-endpoint trace support as observed only for a configured Ethereum endpoint, not a verified built-in free endpoint; no free-endpoint trace support is established for the other listed chains. **Use:** “Only providers that successfully return the required trace data are counted as supported; unsupported or untested endpoints are reported as unsupported/unknown.” |
| 11 | The system achieves 35% cost savings. | **REWORD** | The canonical runtime arithmetic supports a **35% modeled saving**, not an observed 100-transaction billing result. **Use:** “The routing mixture implies a modeled 35% cost reduction under the stated assumptions.” |
| 12 | The paper’s future-work/limitations statement is empirically established. | **REWORD** | Preserve it as a limitation or future-work proposal, not as a measured result. **Use:** “Future work should validate provider coverage, annotation provenance, paired usage, and ranking quality on a frozen independently reviewed workload.” |
| 13 | Top-1 localization is 6.1% (7/115). | **VERIFIED** | `reports/claim_evidence/localization_summary.json` records 115 evaluated transactions, 7 top-1 hits, 6.1% top-1 accuracy, 23 top-3 hits, 36 top-5 hits, 48 top-10 hits, and MRR 0.173. Scope this to the saved localization artifact and function-match protocol. |
| 14 | All 8 frozen-cohort chains have verified free RPC capability. | **REWORD** | `chain_capability_matrix.csv` provides one yes/no observation per listed free endpoint plus an evidence-status explanation. The matrix does not establish universal capability: Ethereum’s observed trace came from a configured endpoint, and the other chains have no recorded free trace success. |
| 15 | WAF results support the claimed security conclusion. | **DROP** | No retained WAF evaluation artifact supports this claim. Remove it rather than present it as a verified experiment. |
| 16 | Table VI supports the claimed additional comparison. | **DROP** | No retained Table VI result artifact was identified for this audit. Remove the empirical claim. |
| 17 | The 20-transaction improvement/result is established. | **DROP** | No retained paired 20-transaction artifact supports the claimed improvement. Remove the empirical claim. |
| 18 | The result can be reproduced locally without paid APIs or LLM calls. | **VERIFIED** | `scripts/reproduce/run_all.py` and `scripts/reproduce/claim_evidence.py` are offline/local and use saved artifacts. `REPRODUCING.md` documents the commands. This verifies the reproduction workflow, not the unsupported paper-scale claims above. |

## Reproduction commands

```bash
.venv/bin/python scripts/reproduce/run_all.py
.venv/bin/python scripts/reproduce/claim_evidence.py
```

The second command only reads the frozen cohort and saved result artifacts. It
does not call an RPC endpoint, model provider, or paid service.
