# FaultSeeker++ submission verification

## Disposition

**PAPER CLAIMS PARTIALLY CLOSED — EXTERNAL EVIDENCE REQUIRED**

The manuscript has been narrowed to evidence-bounded claims. Original
population-level detector, calibration, localization, guidance, WAF, provider,
cohort, and measured-cost claims are not presented as established results.

The revised manuscript is `paper/blockchain_exploit_forensics_survey_ieee.tex`.
Its unsupported result tables were replaced with an evidence-bounded artifact
table, and the calibration section now labels the retained model as
non-production-eligible.

## Commands actually run

| Command | Result |
|---|---|
| `python -m pytest tests/test_claim_closure_ledger.py tests/test_calibration_cost_evidence_audit.py tests/test_calibration_schema.py tests/test_measured_cost_run.py tests/test_batch_e_runtime.py -q -p no:cacheprovider` | 19 passed |
| `python scripts/research/verify_batch_e_result.py` | PASS; R@1=14/40, R@3=27/40, R@5=33/40 |
| `python scripts/reproduce/run_all.py` | All seven retained historical metrics PASS: F1 0.7586, modeled cost 35.0%, localization 6.1%, reentrancy 17, vulnerability strings 82, cohort rows 231, chains 8 |
| `python scripts/reproduce/audit_calibration_cost_evidence.py --root .` | Exit 2; calibration and measured cost evidence blocked as expected |
| `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .` | Exit 0; manifest valid but 14/246 and `BLOCKED-BY-DATA` |
| `python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v3_20261016/cohort_manifest.json --root .` | Exit 0; 20/246 and `BLOCKED-BY-DATA` |
| `python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v4_20261016/cohort_manifest.json --root .` | Exit 0; 22/246 and `BLOCKED-BY-DATA` |
| `python -m pytest tests -x -q -p no:cacheprovider` | 965 passed, 7 skipped, then 1 source-audit failure |
| `pdflatex -interaction=nonstopmode -halt-on-error ...` | Not run: `pdflatex` is unavailable in the environment |

## Retained quantitative evidence

- Historical feature-harness aggregate: F1=0.7586, TP=154, FP=21, TN=979,
  FN=77; proxy/historical scope only.
- Historical localization summary: 7/115 top-1 hits; raw rankings unavailable.
- Frozen Batch E: address-only R@1=14/40, R@3=27/40, R@5=33/40.
- Modeled cost: 35% under retained assumptions; no completed 100-transaction
  measured workload.

## Known local defect

The current dirty `source_resolution_audit.csv` has 69 unresolved rows. The
existing test's historical floor is 70. Clean HEAD has 70, while the dirty
derived audit and summary are stale relative to the current input. Row 111's
dirty `[200]` result is not supported by retained provenance, which records
HTTP 403. The source CSV and derived tracked files were preserved unchanged.

## Required before scientific completion

The remaining requirements are listed in
`EXTERNAL_EVIDENCE_ACQUISITION_PLAN.md`: authenticated cohort and independent
annotation, complete trace coverage, function-level ground truth, measured
routing/cost observations, authorized provider evidence, and any required human
review. No claim is closed by implementation tests alone.
