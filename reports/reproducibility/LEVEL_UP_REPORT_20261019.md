# FaultSeeker++ level-up experiment

## Causal bottleneck account

The saved legacy evidence points to two different ceilings:

1. **Detector:** the current full-system OOF calibrator is driven by eight
   trace-derived calibration features. Static, dynamic, and LLM-style scores
   exist in the harness but are not explicitly fused into that calibration
   stage. Routing and no-routing were identical in paired results, so routing
   is not the current aggregate bottleneck. The previous density experiment
   improved recall but increased FPR; it was not promoted.
2. **Localization:** the dominant ceiling remains candidate coverage. On 114
   eligible rows, 31 target addresses are absent, 15 rows have an address but
   no exact function identity, and 15 have an exact function ranked below
   Top-5. Existing ranker-signal trials found no safe ranking improvement from
   saved count/depth features. Full traces are missing for most address-absent
   rows.

The highest-leverage locally executable intervention was therefore feature-level
detector fusion, while preserving localization changes and avoiding unsupported
trace heuristics.

## Fusion hypothesis

Explicitly add the existing row-local static, dynamic, and LLM-style component
scores to the eight-feature calibration payload. These scores are deterministic
transforms of trace features, but expose clipping and the low-call branch that
the current linear calibrator does not receive as separate inputs.

Evaluation used:

- 115 exploit rows plus 1,000 benign trace rows.
- Same retained legacy ground truth and feature inputs.
- Five deterministic SHA-256 hash folds.
- Training-only fold fitting.
- Fixed threshold `0.5`.
- No new dependencies, provider calls, or external data.

## Result

| Metric | Baseline | Fusion candidate |
|---|---:|---:|
| TP | 72 | 74 |
| FP | 10 | 9 |
| TN | 990 | 991 |
| FN | 43 | 41 |
| Precision | 0.8780 | 0.8916 |
| Recall | 0.6261 | 0.6435 |
| F1 | 0.7310 | 0.7475 |
| FPR | 0.0100 | 0.0090 |
| Brier | 0.035851 | 0.033944 |
| ECE | 0.037711 | 0.036376 |
| Bootstrap F1 CI | [0.6548, 0.7980] | [0.6768, 0.8103] |

Paired comparison:

- Baseline-only correct: `0`
- Candidate-only correct: `3`
- Discordant pairs: `3`
- Continuity-corrected McNemar χ²: `1.3333`

All aggregate metrics moved in the desired direction. The result is materially
better than the accepted legacy baseline, but paired statistical evidence is
weak because only three rows changed. It is an experimental candidate, not
proof of the original 246-row result.

## Evidence and reproducibility

Implementation/evaluator:

```text
scripts/research/evaluate_feature_fusion_calibration.py
```

Retained evidence:

```text
reports/reproducibility/legacy_115_diagnostic/feature_fusion_calibration/
```

The directory contains per-row baseline/candidate predictions, component scores,
subgroup breakdowns, input hashes, configuration, and output checksums.

The previous selector-normalization result remains preserved in:

```text
reports/reproducibility/localization_candidate_coverage_selector_normalization/
```

Frozen Batch E remains read-only and unchanged at R@1 `14/40`, R@3 `27/40`,
R@5 `33/40`.

## Decision

Retain feature fusion as the strongest current experimental architecture
variant. Do not make it the default production scorer until it is reproduced on
an independent, trace-complete cohort. The exact next experiment is a new
immutable held-out localization/detector evaluation with full structured
traces and independent labels; the missing full traces prevent a defensible
local repair of the remaining 31 localization address-coverage failures.
