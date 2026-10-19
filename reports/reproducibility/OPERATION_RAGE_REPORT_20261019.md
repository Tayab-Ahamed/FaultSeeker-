# Operation Rage handoff

## Current state

Current HEAD before this operation was `c9a8baf`. Frozen Batch E was never
rerun or modified. Existing dirty and untracked user files remain untouched.

## Detector loop

The validated full-fusion candidate was independently checked with five
predeclared variants on the same 1,115-row legacy diagnostic population:

| Variant | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 72 | 10 | 990 | 43 | 0.8780 | 0.6261 | 0.7310 | 0.0100 | 0.035851 | 0.037711 |
| Static-only | 74 | 10 | 990 | 41 | 0.8810 | 0.6435 | 0.7437 | 0.0100 | 0.035091 | 0.037912 |
| Dynamic-only | 73 | 10 | 990 | 42 | 0.8795 | 0.6348 | 0.7374 | 0.0100 | 0.035812 | 0.038435 |
| LLM-only | 74 | 10 | 990 | 41 | 0.8810 | 0.6435 | 0.7437 | 0.0100 | 0.034556 | 0.034636 |
| Full fusion | 74 | 9 | 991 | 41 | 0.8916 | 0.6435 | 0.7475 | 0.0090 | 0.033944 | 0.036376 |

Full-fusion F1 improved over baseline in folds 0, 2, and 3, was unchanged in
folds 1 and 4, and Brier improved in all folds. Only three correctness decisions
changed. No significance claim is made.

The exact leakage-safe validation artifact is:

```text
reports/reproducibility/legacy_115_diagnostic/feature_fusion_validation/
```

## Follow-up experiment

One predeclared stronger-L2 check (`0.001 → 0.01`) was run to test whether the
11-feature fusion model was overfitting. It was rejected:

| Metric | Full fusion L2=0.001 | L2=0.01 |
|---|---:|---:|
| TP | 74 | 72 |
| FP | 9 | 11 |
| TN | 991 | 989 |
| FN | 41 | 43 |
| F1 | 0.7475 | 0.7273 |
| FPR | 0.0090 | 0.0110 |
| Brier | 0.033944 | 0.035604 |
| ECE | 0.036376 | 0.038242 |

Paired comparison favored the existing fusion model: 4 baseline-only correct,
0 candidate-only correct, χ² `2.25`.

Evidence:

```text
reports/reproducibility/legacy_115_diagnostic/fusion_regularization/
```

No arbitrary hyperparameter search was performed after this negative result.

## Localization

The selector-normalization improvement remains:

- Exact function coverage: `66/114 → 68/114`
- Top-1: `24/114 → 24/114`
- Top-3: `48/114 → 50/114`
- Top-5: `51/114 → 53/114`

The remaining 31 address-absent cases are limited primarily by missing full
structured traces. No unsupported function identities were invented.

## Original-claim execution

The cohort validator ran successfully but confirms the original detector cohort
is still data-blocked:

```text
accepted_rows: 14
additional_verified_rows_needed: 232
target_count: 246
status: BLOCKED-BY-DATA
```

No original paper claim became independently reproducible.

## Verification

Passed:

```text
12 localization/ranker/serializer tests
9 candidate-generation tests
python scripts/research/verify_batch_e_result.py
```

Frozen Batch E remains R@1 `14/40`, R@3 `27/40`, R@5 `33/40`.

## Next action

Stop local tuning on this exposed legacy cohort. The highest-value next step is
to obtain a new immutable, trace-complete, independently adjudicated cohort for
fusion validation and localization candidate recall. Clean Linux Docker/PDF
verification remains a separate T13 dependency.
