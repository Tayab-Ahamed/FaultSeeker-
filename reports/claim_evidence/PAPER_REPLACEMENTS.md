# Phase 3 Paper Replacements

This document contains ready-to-paste IEEE-style wording for the ten claims
marked **REWORD** in `reports/claim_evidence/CLAIMS_STATUS.md`. Each entry
contains one replacement sentence and a repository-relative evidence reference.
The wording is scoped to the saved local artifacts and does not assert
unsupported paper-scale or newly rerun empirical results.

## REWORD claims

### Claim 1

**Replacement sentence:** The frozen analysis cohort contains 231 rows; every retained row has a syntactically valid transaction hash and at least one recorded source URL.

**Evidence reference:** `reports/claim_evidence/summary.json` (`rows: 231`, `rows_missing_source_or_hash: 0`); `reports/claim_evidence/cohort_provenance_gaps.csv` (no gap rows).

### Claim 2

**Replacement sentence:** The offline headline reproduction passes, whereas the full suite reports 960 passed, 1 failed, and 7 skipped; the failure concerns immutable gzip-header serialization drift.

**Evidence reference:** `scripts/reproduce/run_all.py`; `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 2 status and full-suite result).

### Claim 4

**Replacement sentence:** The frozen cohort contains 82 distinct vulnerability-label strings, of which 36 carry an existing SWC classification and 46 do not.

**Evidence reference:** `reports/claim_evidence/summary.json` (`distinct_vulnerability_label_strings: 82`, `labels_with_existing_swc_mapping: 36`, `labels_without_existing_swc_mapping: 46`); `reports/claim_evidence/vulnerability_swc_mapping.csv`.

### Claim 6

**Replacement sentence:** Seventeen frozen rows carry a reentrancy label string.

**Evidence reference:** `reports/claim_evidence/summary.json` (`reentrancy_label_string_count: 17`); `reports/claim_evidence/reentrancy_rows.csv` (17 rows whose stored label contains “reentran”).

### Claim 8

**Replacement sentence:** Saved feature-harness aggregates include rows for Static proxy, Dynamic trace-rule, LLM-only, FaultSeeker++ (Ours), -FAEGL, -TIG graph, -Learned calib, and -LLM routing; these rows should not be presented as a newly rerun or independently audited comparison.

**Evidence reference:** `reports/claim_evidence/table_v_saved_results.csv` (`status: SAVED_FEATURE_HARNESS_AGGREGATE` for all eight rows).

### Claim 9

**Replacement sentence:** Each retained row includes a syntactically valid transaction hash and at least one recorded source URL; field presence alone does not establish annotation authenticity, so any synthetic or unverified label should be identified explicitly.

**Evidence reference:** `reports/claim_evidence/cohort_provenance_gaps.csv` (no missing source URL or transaction-hash fields); `reports/claim_evidence/summary.json` (`rows_missing_source_or_hash: 0`).

### Claim 10

**Replacement sentence:** We will count a provider as supported only when it successfully returns the required trace data; endpoints without such evidence will be reported as unsupported or unknown.

**Evidence reference:** `reports/claim_evidence/chain_capability_matrix.csv` (`evidence_status` and `free_endpoint_trace_support_observed` columns); `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 10 status).

### Claim 11

**Replacement sentence:** Under the stated assumptions, the routing mixture implies a modeled 35% cost reduction; this figure is not an observed billing measurement.

**Evidence reference:** `scripts/reproduce/modeled_cost.py`; `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json`; `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 11 status).

### Claim 12

**Replacement sentence:** Future work should validate provider coverage, annotation provenance, paired usage, and ranking quality on a frozen, independently reviewed workload.

**Evidence reference:** `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 12 status and preserved future-work wording).

### Claim 14

**Replacement sentence:** For the eight chains represented in the frozen cohort, universal free-RPC trace capability is not established: the recorded Ethereum trace used a configured endpoint rather than a verified built-in free fallback, and no free-endpoint trace success is recorded for the remaining cohort chains.

**Evidence reference:** `reports/claim_evidence/summary.json` (`chains: 8`); `reports/claim_evidence/chain_capability_matrix.csv` (Ethereum endpoint note and `NOT_OBSERVED` status for the other listed endpoints).

## DROP claims: clean removal notes

### Claim 15 — WAF result/security conclusion

**Removal note:** Remove the WAF empirical-result sentence(s), security conclusion, and any associated WAF result reference; do not replace them with a measured result.

**Evidence reference:** `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 15: DROP; no retained WAF evaluation artifact).

### Claim 16 — Table VI comparison

**Removal note:** Remove the claimed additional Table VI comparison and any associated empirical interpretation; do not retain a table or sentence implying that the comparison was evaluated.

**Evidence reference:** `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 16: DROP; no retained Table VI result artifact identified).

### Claim 17 — 20-transaction improvement/result

**Removal note:** Remove the claimed improvement/result over 20 transactions and any associated quantitative conclusion; do not present it as an experiment without a retained paired artifact.

**Evidence reference:** `reports/claim_evidence/CLAIMS_STATUS.md` (Claim 17: DROP; no retained paired 20-transaction artifact).
