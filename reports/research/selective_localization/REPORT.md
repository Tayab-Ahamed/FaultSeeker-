# Selective localization experiment

## Verdict

**REJECTED_ON_HELD_OUT_RETAINED_TEST** — this result is held-out evidence for the fixed grouped split, not a generalization claim.

H1 asks whether abstention can remove incorrect high-confidence localization decisions while retaining useful coverage. The fixed baseline always returns the retained ranked prediction list. The selective policy abstains when the fixed evidence-sufficiency score is below the validation-selected threshold.

## Dataset and leakage controls

- Full retained universe: 115 rows.
- Run-level evidence failures: 5 rows; these are outside the ranked-prediction evaluation.
- Eligible ranked-prediction rows: 110.
- Grouping: target-contract address, used only for partitioning; group overlap is [].
- Split counts: train=48, validation=31, test=31.
- Validation minimum coverage constraint: 50%.
- No ground-truth label, target address, or rank correctness enters the score features.

## Evidence failures

- Failed retained runs: 5.
- Eligible rows with no saved trace text: 4.
- Eligible rows with no parsed trace calls: 17.
- Eligible rows with no selector metadata: 106.

## Fixed score

The score uses only saved prediction-time evidence: trace availability, non-empty candidates, parsed trace-call strength, top-ranked supporting-path strength, whether the top candidate appears in the saved trace, the fraction of top-five candidates observed in the trace, and selector metadata availability.

- Weights: `{"candidate_available": 0.15, "selector_available": 0.05, "top1_observed_in_trace": 0.15, "top1_support_strength": 0.15, "top5_observed_fraction": 0.1, "trace_available": 0.2, "trace_call_strength": 0.2}`
- Selected threshold: `0.53333333`
- Selection rule: minimize validation top-1 error; tie-break by lower coverage while retaining the minimum floor, then larger threshold

## Held-out test results

| Policy | Predictions | Coverage | R@1 | R@3 | R@5 | Top-1 error |
|---|---:|---:|---:|---:|---:|---:|
| Always return ranking | 31/31 | 1.0000 | 7/31 (0.2258) | 11/31 (0.3548) | 13/31 (0.4194) | 0.7742 |
| Abstain below threshold | 18/31 | 0.5806 | 3/18 (0.1667) | 4/18 (0.2222) | 6/18 (0.3333) | 0.8333 |

- Test abstention coverage: 13/31 abstained.
- Removed predictions: {"1": {"correct_predictions_removed": 4, "incorrect_predictions_removed": 9}, "3": {"correct_predictions_removed": 7, "incorrect_predictions_removed": 6}, "5": {"correct_predictions_removed": 7, "incorrect_predictions_removed": 6}}
- Grouped bootstrap 95% intervals: {"baseline_recall_at_1": [0.09375, 0.375], "baseline_recall_at_3": [0.1875, 0.53333333], "baseline_recall_at_5": [0.25, 0.6], "baseline_top1_error": [0.625, 0.90625], "error_rate_delta_selective_minus_baseline": [-0.06666667, 0.19924099], "selective_coverage": [0.4, 0.75757576], "selective_recall_at_1": [0.0, 0.35714286], "selective_recall_at_3": [0.05263158, 0.4375], "selective_recall_at_5": [0.11764706, 0.57142857], "selective_top1_error": [0.64285714, 1.0]}

## Coverage versus error

The complete validation-derived threshold curve is stored in `metrics.json` under `threshold_curve`. It is descriptive; the final threshold was selected on validation only and then evaluated once on test.

## Limitations

- This is a small 110-row retained, provider-pinned, LLM-free evaluation, not the original 246-row paper cohort.
- The five failed rows cannot be evaluated as ranked predictions and are reported separately rather than silently dropped from the retained-universe accounting.
- Target-contract grouping is a conservative split control derived from ground truth; it is not a prediction feature.
- The fixed score was not learned. The threshold is selected from validation, while weights and the 50% minimum-coverage rule are fixed in the experiment configuration.
- Results are exploratory/held-out evidence for this retained dataset and do not establish generalization.
