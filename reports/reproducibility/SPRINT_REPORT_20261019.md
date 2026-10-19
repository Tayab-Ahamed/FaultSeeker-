# FaultSeeker++ 24-hour execution sprint

## Scope

This sprint continued from commit `efc6c9d` and preserved frozen Batch E and
all pre-existing dirty/untracked workspace artifacts. No network/provider calls,
transactions, fabricated labels, or human-study responses were used.

## 1. Implementation changes

### Accepted localization fix

Commit `a7bab37` changed
`benchmark/generate_pipeline_predictions.py` so exactly-eight-hex-digit
function labels are serialized as canonical `0x`-prefixed selectors. The
serializer preserves explicit address, selector, rank, and call-depth metadata.

Regression coverage is in
`tests/test_function_identity_normalization.py`.

### Detector candidate experiment

`scripts/research/evaluate_trace_density_calibration.py` evaluates, but does
not promote, one new row-local calibration feature:

```text
address_count / max(functioncall_count, 1)
```

The feature was motivated by the retained error analysis: false positives have
high address fan-out relative to their call volume.

## 2. Successful experiments

### Localization selector normalization

Same-input replay on 114 eligible provider-pinned rows:

| Metric | Baseline | Candidate |
|---|---:|---:|
| Address candidates | 83/114 | 83/114 |
| Exact function candidates | 66/114 | 68/114 |
| Top-1 | 24/114 | 24/114 |
| Top-3 | 48/114 | 50/114 |
| Top-5 | 51/114 | 53/114 |
| Ranking-only failures | 15 | 15 |

There were no Top-1/3/5 regressions. The two recovered rows contained bare
selectors `ba381f8f` and `925d400c` while ground truth used the canonical
`0x...` form.

Evidence:

```text
reports/reproducibility/localization_candidate_coverage_selector_normalization/
```

### Localization failure-source investigation

Baseline categories across the same 114 rows:

- 31 target addresses absent from candidates.
- 15 target addresses present but target function identity absent.
- 15 exact target functions present but ranked below Top-5.
- 2 evaluation/identity-mapping defects, fixed by selector normalization.
- 0 invalid/ambiguous ground-truth rows.

The 31 address-absent rows were checked against the available raw inputs and
trace parser:

- 28 do not contain the target address in the retained `cast.output_tail`.
- 2 can be recovered by the existing trace parser.
- 1 contains the target address only in an event/parameter line, not a call
  line with a function identity.

The exact missing artifact for further recovery is full call-trace/call-tree
data for those rows. No event-only address heuristic was added.

### Legacy detector trace-density candidate

This remains diagnostic evidence only, not the original 246-row claim.

| Metric | Baseline | Candidate |
|---|---:|---:|
| TP | 72 | 78 |
| FP | 10 | 11 |
| TN | 990 | 989 |
| FN | 43 | 37 |
| Precision | 0.8780 | 0.8764 |
| Recall | 0.6261 | 0.6783 |
| F1 | 0.7310 | 0.7647 |
| FPR | 0.0100 | 0.0110 |
| Brier | 0.035851 | 0.029222 |
| ECE | 0.037711 | 0.028766 |
| Bootstrap F1 CI | [0.6548, 0.7980] | [0.6977, 0.8235] |

Paired comparison: 2 baseline-only correct rows, 7 candidate-only correct rows,
9 discordant pairs, continuity-corrected McNemar chi-square `1.7778`.

Decision: retain as a promising legacy diagnostic candidate, but do not promote
to production. It adds one false positive, increases FPR, slightly lowers
precision, and does not establish statistically significant paired superiority
on this historically exposed cohort.

Evidence:

```text
reports/reproducibility/legacy_115_diagnostic/trace_density_calibration/
```

## 3. Tests and reproducibility gates

Passed:

```text
12 localization/ranker/serializer tests
9 candidate-generation tests
python scripts/research/verify_batch_e_result.py
```

Frozen Batch E remains unchanged:

- R@1: `14/40`
- R@3: `27/40`
- R@5: `33/40`

Full offline suite:

```text
1061 passed, 7 skipped, 1 failed
```

The single failure is the preserved source-audit mismatch:

```text
summary["unresolved_rows_attempted"] == 69
test requires >= 70
```

GNU `make` is unavailable on this Windows host, so the Makefile test command
was executed directly. Docker verification is blocked because the Docker
Desktop Linux engine is unavailable. PDF/TeX verification was not possible.

## 4. Original claim status

No original paper claim was promoted to empirical reproduction.

- T01 detector F1/FPR: `EXTERNALLY_BLOCKED`; the 115-row result is diagnostic
  only and cannot substitute for the 246-row authenticated cohort.
- T09 localization/guidance: `IMPLEMENTED_NOT_VALIDATED`; the selector fix is
  validated on the saved 114-row exploratory population, not a new held-out
  model/source run.
- T10 calibration: `EXTERNALLY_BLOCKED`; the density candidate is not a
  disjoint production evaluation.
- T13 reproducibility: `IN_PROGRESS`; local tests run, but clean Linux Docker,
  full clean-environment verification, and PDF compilation remain unavailable.
- Other original claims remain in their existing blocked or user-input states;
  no denominators or target definitions were changed.

## 5. Files and commits

- `a7bab37 fix: canonicalize localization selector identities`
- `benchmark/generate_pipeline_predictions.py`
- `tests/test_function_identity_normalization.py`
- `scripts/research/evaluate_localization_candidate_coverage.py`
- `scripts/research/evaluate_trace_density_calibration.py`
- `reports/reproducibility/localization_candidate_coverage_selector_normalization/`
- `reports/reproducibility/legacy_115_diagnostic/trace_density_calibration/`
- `reports/reproducibility/ORIGINAL_CLAIM_MISSION.json`
- `reports/reproducibility/AUTONOMOUS_WORKLOG.md`

## Highest-value next action

Obtain the missing full structured call traces and independent function-level
adjudication for a new immutable held-out localization cohort. Locally, the
remaining address-absent failures cannot be safely repaired from the retained
trace tails, and further ranker heuristics would be unsupported.
