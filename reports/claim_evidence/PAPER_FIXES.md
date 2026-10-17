# Paper fixes required by the strict audit

This file is the sentence-level correction ledger for the 18-claim audit.
“Before” is the prior `CLAIMS_FINAL.md` disposition; “after” is the strict
disposition in the updated `CLAIMS_FINAL.md`. No paper source was edited.

## Claim-by-claim corrections

| Claim | Before → after | Paper sentence/category requiring correction | Evidence and blocker proof | Exact safe wording |
|---:|---|---|---|---|
| 1 | VERIFIED → REWORD | “231 authentic/provenance-backed evaluated rows” | `reports/claim_closure/local_snapshot/claim_report.md` records accepted_rows=0 and 231 missing ground-truth, independent annotation, independent-source, receipt, trace, transaction, and verification fields. | “The frozen fca6b99 analysis CSV has 231 rows with recorded hash/source fields; authenticity and independent annotation were not established.” |
| 2 | VERIFIED → VERIFIED (local-only scope) | “The original 201 tests/reproduction suite passes” | `reports/canonical_history/PAPER_VS_REPO.md` and the canonical closure record support 201 original tests passed with unchanged original sources. This does not support paper empirical results. | “The 201 original test sources are unchanged and the canonical local record reports 201 original tests passed.” |
| 3 | VERIFIED → REWORD | “Ten EVM chains; Ethereum 47.6%” and any sole “231-row cohort” wording | `reports/canonical_history/cohort_history.json` shows eight chains for 183, 213, 231, and 246 row versions; frozen fca6b99 is 132/231 Ethereum (57.1429%). | “The frozen fca6b99 CSV has eight chain strings and 132/231 Ethereum rows (57.1429%); this is not the paper’s ten-chain population.” |
| 4 | VERIFIED → REWORD | “80+ vulnerability types with SWC/DASP labels” | `reports/claim_evidence/vulnerability_swc_mapping_reviewed.csv` counts 82 strings, with 36 existing mappings and 46 no-equivalent entries. Labels are not independently adjudicated semantic classes. | “The frozen CSV contains 82 distinct label strings; 36 retain an existing SWC classification and 46 have no SWC equivalent in the reviewed scope.” |
| 5 | VERIFIED → REWORD | “Simple 6.5%, Moderate 33.3%, Complex 32.5%, Exceptionally Complex 27.6%” | `class_proportions.csv` gives 8.2251/26.8398/39.3939/25.5411%; `PAPER_VS_REPO.md` says authentic trace-based class adjudication is unavailable. | “The frozen CSV stores 19/62/91/59 rows in the four stored classes (8.2251/26.8398/39.3939/25.5411%).” |
| 6 | VERIFIED → REWORD | “17 reentrant incidents” or paper’s 18/246 incident result | `reentrancy_replay_verification.csv` has 17 labeled rows, two with retained trace artifacts and 15 without; it records zero verified reentrant rows because trace presence alone is not incident adjudication. | “Seventeen frozen rows carry a reentrancy label string; two have retained traces and fifteen do not, but independently verified incident count is not established.” |
| 7 | VERIFIED → UNVERIFIABLE | Table V SSTORE detector P=.89, R=.83, F1=.86; structural/repeated baselines and 17/29 pp gains | `reports/claim_closure/claims/13.json` marks the paper metrics unverified; `PAPER_VS_REPO.md` says canonical recompute evaluated zero transactions. `table_v_saved_results.csv` is a different feature-harness target. | “Remove the paper Table V empirical sentence. A separate saved feature-harness aggregate reports F1=0.7586 on 1,231 represented rows.” |
| 8 | REWORD → UNVERIFIABLE | Table IV baseline/ablation comparison and adversarial-retention result | `reports/research_results/research_tables.tex` claims paper-scale values; offline rerun status records full F1=.7586, -TIG=.6531, while saved -TIG=.6565. `adversarial_robustness.csv` has five proxy rows but no raw N=250 challenged production cases. | “Saved local proxy aggregates and a perturbation table exist, but the paper’s Table IV ablation and adversarial-retention experiment was not reproduced.” |
| 9 | VERIFIED → REWORD | “All cohort entries are real transactions and labels” | `source_resolution_audit.csv` proves only syntactic hash validity, recorded URL fields, and 161 resolved rows/70 unresolved rows. It cannot prove incident truth or annotation provenance. | “Each frozen row has a syntactically valid hash field and recorded source URL field; these fields do not establish real transactions or correct labels.” |
| 10 | REWORD → REWORD | “The system supports all named providers/chains” | `chain_capability_matrix_final.csv` records zero usable free historical traces across eight listed endpoints; `chain_capability_matrix.csv` says configured Ethereum observation is not free-endpoint proof. | “Only a provider returning the required trace response is counted as supported; unobserved or rejected endpoints remain unsupported/unknown.” |
| 11 | REWORD → REWORD | “The system achieves 58% overall inference cost saving” | `measured_cost_run.json` records N=100 completed 0 because no tracked preregistered 100-ID/50-30-20 selection manifest exists; `cost_zero_spend_proof.json` records no dotenv load, key use, provider call, or model dispatch. `PAPER_VS_REPO.md` computes 35% overall mixture reduction; 58.3333% is Tier-2-only. | “No measured cost result was obtained (N=100 completed 0; extension not started) because the preregistered selection manifest is absent. The retained 50/30/20 assumptions imply only a modeled 35.0% reduction ($0.039 vs $0.060/query).” |
| 12 | REWORD → REWORD | Any future-work/limitations text presented as an empirical finding | `reports/provenance_hunt/experiments/measurement_frontier.json` and closure decisions list missing independent cohort, paired usage/quality, provider, and confidence evidence. | “Future work should validate these quantities on a frozen independently reviewed workload.” |
| 13 | VERIFIED → REWORD | “Top-1 localization is 6.1% (7/115)” as a reproduced paper result | `localization_summary.json` stores 7/115 and MRR=.173, but `PAPER_VS_REPO.md` marks it recorded-not-reproduced; raw rankings are unavailable and the denominator includes a duplicate transaction. | “The retained summary records 7/115 target hits (6.09%, rounded to 6.1%) under the function-match protocol; raw prediction replay was unavailable.” |
| 14 | REWORD → REWORD | “All eight frozen-cohort chains have verified free RPC capability” | `chain_capability_matrix_final.csv`: no endpoint has a usable historical trace result. | “The eight-chain free-endpoint probe produced no usable historical trace response.” |
| 15 | DROP → DROP | Compound/cToken legitimate recursive case study | `reports/claim_closure/claims/15.json` proves the narrative has no exact transaction hash, trace, or source linkage. | Remove the case-study sentence entirely. |
| 16 | DROP → DROP | Table VI PMS/CES/TCS/LCS category averages | `reports/claim_closure/claims/28.json` requires raw production per-function vectors; only an aggregator contract test exists. | Remove Table VI empirical category averages entirely. |
| 17 | DROP → DROP | “20 randomly selected cases improved from 68% to 81%” | `reports/claim_closure/claims/29.json` says no paired study exists; `guidance.json` is `BLOCKED-BY-DATA` with zero accepted rows. | Remove the 20-case improvement sentence entirely. |
| 18 | REWORD → VERIFIED (workflow-only) | “Results can be reproduced locally without paid APIs/LLM calls” | `scripts/reproduce/run_all.py`, `scripts/reproduce/claim_evidence.py`, `REPRODUCING.md`, and `FINAL_REPORT.md` retain offline commands and no-provider-call scope. | “The retained offline reproduction workflow runs without paid APIs or model-provider calls; this does not reproduce unsupported paper-scale claims.” |

## Required exact paper corrections outside the numbered table

### Dataset, annotation, and repository row count

* **“1,059 annotated exploit transactions”** must be split into the 231-row
  frozen CSV and 828 source-backed candidates. The repository audit says the
  828 rows are not all validated strict labels. The 231 frozen rows also
  contain three `TODO: Needs Annotation` strings, and only 115 original ground-
  truth JSON files cover 114 unique hashes. Safe wording: “The repository
  contains a 1,059-row exploit research pool; 231 rows are in the frozen
  analysis CSV and 828 are source-backed candidates pending strict promotion.”
  Evidence: `reports/canonical_history/PAPER_CLAIM_AUDIT.md`,
  `reports/canonical_history/cohort_history.json`.
* **“11,059 total (1,059 exploit + 10,000 benign)”** must not be called a
  disjoint evaluation population: the 1,059 pool includes the 231 strict rows.
  The benign labels are address-label candidates; the extractor did not run on
  them in the historical audit. Evidence: `PAPER_CLAIM_AUDIT.md` and
  `reports/canonical_history/PAPER_VS_REPO.md`.
* **“Six incident sources, two independent corroborating sources, two
  qualified annotators, approximately 8% disagreement”** is unsupported.
  Source URLs and counts are not a per-row independence/consensus ledger, and
  no annotator attestations or disagreement log is retained. Evidence:
  `reports/canonical_history/PAPER_VS_REPO.md`, claims 3/4 in
  `reports/claim_closure/claims/`.
* **183 versus 231 versus 246** are different repository CSV versions, not
  interchangeable denominators. Use the frozen fca6b99 231-row wording only
  when naming that exact snapshot; the current CSV has 183 rows and the early
  version has 246 unique rows with 15 malformed hashes. Evidence:
  `reports/canonical_history/cohort_history.json`.

### Table IV / ablation / adversarial retention

* The paper’s Table IV-style headline values (F1=.969, FPR=.003, CI
  [.961,.975]) are not supported by the saved current aggregate. The retained
  full-system feature-harness row is TP=154, FP=21, TN=979, FN=77, F1=.7586,
  over 1,231 represented rows. Evidence:
  `reports/research_results/research_tables.tex`,
  `reports/claim_evidence/table_v_saved_results.csv`,
  `reports/honest_results/baseline_comparison.csv`.
* The saved -TIG value is .6565, but the byte-pinned offline rerun is .6531
  (TP=128, FN=103). Report the disagreement; do not tune a threshold to make
  them match. Evidence: `reports/canonical_history/PAPER_VS_REPO.md` and the
  8e02f92c rerun status artifact.
* The paper’s **N=250 per attack type** and retention `rho >= .94` sentence is
  not verified. The retained CSV has five proxy rows with baseline/perturbed
  scores, but no raw challenged production corpus, execution records, or N=250
  denominator. Its fake-event row has delta 0.00, while the paper table claims
  -0.02. Evidence: `reports/honest_results/adversarial_robustness.csv`,
  `reports/honest_results/honest_research_tables.tex`,
  `reports/research_results/research_tables.tex`.

### Cost, routing, WAF, and guidance

* **“Approximately 58% overall inference saving”** is contradicted by the
  stated mixture: $0.039/$0.060 gives 35.0%; 58.3333% is only
  ($0.12-$0.05)/$0.12 for Tier 2. No 100-transaction paired usage/pricing/
  quality log exists. Evidence: `cost_local_model_check.txt`,
  `reports/canonical_history/PAPER_VS_REPO.md`, claim 18.
* **“Approximately 40% clean traffic skips Stage 2”** is unmeasured as a
  population rate; the mechanism test does not supply a verified benign
  workload or paired latency observation. **“23% of Cloudflare challenges
  bypassed”** is also unsupported: RPC fallback success is not a WAF-challenge
  denominator. Evidence: claims 21 and 27, `reports/canonical_history/PAPER_VS_REPO.md`.
* **“20 randomly selected cases, 68% to 81%”** has no selection policy,
  paired rankings, or accepted cases. The binary n=20 resolution is five
  percentage points, and the retained guidance experiment has zero accepted
  rows. Evidence: `reports/claim_closure/claims/29.json` and `guidance.json`.

### DAppFL and external comparisons

* The sentence **“Analysts spend 16.7 h per incident [5]”** is not repository
  evidence and must not be presented as validated by this audit. The historical
  audit explicitly says to verify it against DAppFL before submission; the repo
  only retains a DAppFL source URL, not a checked extraction of that statistic.
  Safe wording: “A cited external source reports an analyst-time estimate;
  this repository audit does not independently verify the 16.7-hour value.”
  Evidence: `reports/canonical_history/snapshots/50853e461b635bc1e2cc088b91957cdac2a610d2/PAPER_CLAIM_AUDIT.md`,
  `reports/provenance_hunt/source_manifest.json`.
* Any claim that FaultSeeker++ empirically outperforms DAppFL is unsupported:
  no same-input DAppFL run, matched labels, metric definition, or paired
  predictions are retained. Safe wording: “DAppFL is a cited related system;
  no repository artifact supports a quantitative comparison.”

* A new measurement on the imported original FaultSeeker benchmark is now
  available, but it must not be substituted for the upstream Table II values:
  the LLM-free run covered 115 files with 2 trace-success cases, 113 failures,
  and Recall@1/3/5 of 0/0/0. The API-backed full-pipeline run was not
  dispatched because free-tier eligibility was not verified and the trace/source
  prerequisite failed for 113 cases. Evidence:
  `reports/original_benchmark/llm-free/original-v1-seed20261017/manifest.json`.

### Table VI, case study, and mechanism scope

* Remove all Table VI category averages (`.82/.71/.76/.73/.76`, etc.). No raw
  PMS/CES/TCS/LCS vectors exist for the paper cohort.
* Remove or qualify the Compound/cToken “legitimate recursion” case: the
  narrative lacks an exact hash and trace/source binding.
* Table IV signal weights are mechanism definitions, not empirical validation;
  the retained table has `write_before_and_after=0.20`, while the canonical
  paper/repository audit identifies a paper `.10` mismatch. Evidence:
  `reports/research_results/research_tables.tex` and
  `reports/canonical_history/PAPER_VS_REPO.md`.
* “Six provider families,” live chain support, and quality/ranking bounds are
  implementation or external-conformance claims until live provider outputs
  and paired quality observations are retained. Adapter-construction tests do
  not establish live service support.
