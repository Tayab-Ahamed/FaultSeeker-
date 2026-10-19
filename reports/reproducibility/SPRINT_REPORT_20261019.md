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

## 6. Continuation execution log

The continuation directive executed three additional work units without
touching Batch E or the pre-existing dirty/untracked evidence files:

1. `2dacfcb feat: audit recovered original transaction traces` added a
   read-only audit of the previously captured dRPC callTracer run. It verified
   9 transaction-hash matches, recovered 4 original-benchmark rows with the
   target address observed in trace, and matched all 4 imported labels to typed
   public signatures and observed selectors. This is per-case evidence, not a
   paper-scale scorer reproduction.
2. `ebeeaae feat: preserve batch d and multichain trace evidence` committed the
   frozen Batch D artifacts and the bounded multichain RPC evidence. Batch D
   remains a 10-row convenience sample with one score pass, 40 RPC requests,
   zero billing prompts, and address+selector R@1/3/5 of `2/10`, `3/10`, and
   `4/10`. The Batch D freeze hash remains
   `e349997c875542ffb85a2205dbc4357e31d547c7dffb3cf1f12aebf3634becf7`.
3. The machine-readable claim ledger was regenerated at
   `reports/claim_closure/local_snapshot/claim_ledger.json`: 31 claims, 11
   verified implementation claims, 4 contradicted-by-current-evidence claims,
   14 externally blocked claims, 2 unverified claims, and zero reproduced
   empirical claims.

Continuation checks: recovered-trace tests `2 passed`, Batch D safety tests
`8 passed`, claim-ledger tests `8 passed`, and the Batch E verifier passed with
`14/40`, `27/40`, and `33/40` unchanged. The remaining full-suite mismatch,
Docker Linux engine limitation, and PDF/TeX limitation remain unchanged.

The latest full offline suite was rerun after the continuation artifacts were
added: `1065 passed, 7 skipped, 1 failed` in 125.11 seconds. The only failure
remains `tests/test_t3_evidence_audits.py::test_local_source_audit_is_network_free_and_keeps_adjudication_separate` because the preserved source-resolution artifact contains 69 unresolved rows, while that pre-existing assertion requires at least 70. The input has 231 rows with 69 `UNRESOLVED` statuses and no omitted zero-URL row, so no evidence-preserving source correction is available; the assertion and source evidence were left unchanged.
