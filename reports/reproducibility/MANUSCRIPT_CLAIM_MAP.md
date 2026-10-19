# Manuscript-to-evidence claim map

This map is tied to `paper/blockchain_exploit_forensics_survey_ieee.tex`. Claim
titles use the canonical repository registry in `benchmark/claim_registry.py`.
Where the original paper sentence is not present in the current manuscript, the
map says so explicitly; a ledger entry alone is not treated as manuscript text.

| ID | Manuscript location / current wording | Evidence and command | Final disposition |
|---:|---|---|---|
| 1 | Reproducibility discussion, Sec. IX; no local-branch publication sentence | `reports/claim_closure/sources/public_repository.json`; publication evidence is external | External publication requirement remains explicit |
| 2 | No current quantitative manuscript sentence | `python -m pytest tests -x -q -p no:cacheprovider` | Current suite is not clean because of the dirty source-audit snapshot |
| 3 | Sec. IX: root manifest 14/246 and versioned maximum 22; not an authenticated 246-row claim | `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .` | Narrowed; target cohort not claimed as complete |
| 4 | Sec. IX and dataset discussion require source/annotation evidence; no claim of two independent sources remains | Cohort manifest and bound-artifact validator | External adjudication remains required |
| 5 | Dynamic-forensics discussion mentions cross-chain variability, not a ten-chain result | Versioned manifests and capability evidence | No ten-chain/47.6% result claimed |
| 6 | Dataset discussion describes label provenance requirements, not a validated taxonomy count | Cohort and annotation admission artifacts | No semantic-label count claimed |
| 7 | No class-percentage result remains | Frozen CSV counts are descriptive only | Removed from quantitative results |
| 8 | No 18-incident result remains | Reentrancy audit records label strings only | Removed from quantitative results |
| 9 | FAEGL and trace/source evidence model, Secs. IV, VI, XI | Local detector and storage tests | Verified implementation scope only |
| 10 | Storage/graph signals are described algorithmically | Paper detector and weight tests | Verified implementation scope only |
| 11 | Fallback modes and utility thresholds, Sec. IV | `tests/test_paper_tiers.py`, fallback tests | Verified implementation scope only |
| 12 | Failure handling and fallback caps, Sec. XI | `tests/test_paper_fallback.py` | Verified implementation scope only |
| 13 | Original detector table removed; no paper F1 claim remains | Saved proxy aggregate only: `reports/honest_results/baseline_comparison.csv` | Historical proxy, not paper reproduction |
| 14 | Original percentage-point gain sentence removed | Paired experiment remains data-blocked | Removed; external paired data required |
| 15 | No Compound case-study sentence remains | `reports/reconciliation/recovered_trace_audit.json` recovers 4 original rows with target-address traces and typed selector matches; no complete case-study package or executed paper scorer | Removed; partial per-case evidence retained |
| 16 | No Table VI category-average result remains | Production component vectors absent | Removed |
| 17 | No 20-case guidance result remains | No preregistered paired study | Removed |
| 18 | Sec. IX table reports only 35% modeled cost (`$0.039` vs `$0.060`) | `python scripts/reproduce/audit_calibration_cost_evidence.py --root .` | Modeled-not-measured; 100-run claim removed |
| 19 | Sec. XI says deterministic components collect facts before LLM reasoning | Stage-one local tests | Verified implementation scope only |
| 20 | Sec. XI distinguishes trace/source/proxy failure states | Local control-flow tests | Verified implementation scope only |
| 21 | No 40% benign-prefilter result remains | No independent benign paired workload | Removed; external workload required |
| 22 | Introduction and FAEGL section describe localization as a reference algorithm, not measured population performance | Batch E verifier and saved localization summary | Address-only/historical scopes retained; no generalization |
| 23 | Sec. V calibration equations now explicitly state that the retained model is not production-eligible | Calibration audit and schema tests | Protocol/implementation only; no validated probability claim |
| 24 | No quantitative HITL improvement claim remains | HITL behavior tests | Implementation scope only |
| 25 | Sec. VI discusses RPC/trace availability limitations | RPC mechanism tests and capability artifacts | Broader live capability remains external |
| 26 | Sec. VI explains executed traces, storage, and proxy context | Historical replay and compiled-EVM tests | Tool/fixture evidence only; not cohort-wide validation |
| 27 | No WAF percentage remains | No authorized challenge denominator | Removed |
| 28 | No category-average table remains | No production PMS/CES/TCS/LCS vectors | Removed |
| 29 | No guidance percentage remains | No paired selection/policy/outcomes | Removed |
| 30 | Sec. IX describes the artifact as reproducibility infrastructure, not exact paper reproduction | `python scripts/reproduce/run_all.py` and claim ledger | Offline workflow retained; paper-scale reproduction remains unverified |
| 31 | Runtime/reproducibility claims are repository metadata, not manuscript performance claims | Runtime-layout tests and pinned Docker/lockfile | Local packaging scope only |

## Quantitative statements retained in the manuscript

The revised manuscript retains only values with explicit scope:

- Saved feature-harness aggregate: F1 0.7586 with TP=154, FP=21, TN=979,
  FN=77; historical proxy over represented rows, not an authenticated study.
- Historical localization summary: 7/115 top-1 hits; raw rankings are not
  retained for independent replay.
- Frozen Batch E: address-only R@1=14/40, R@3=27/40, R@5=33/40.
- Modeled routing arithmetic: 35% (`$0.039` hybrid versus `$0.060` cloud-only);
  no measured 100-transaction run exists.

All other original headline numerical claims are removed, narrowed, or marked as
requirements for future evidence in the repository acquisition plan.
