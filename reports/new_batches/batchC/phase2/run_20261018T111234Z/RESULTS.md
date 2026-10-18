# Batch C phase 2 results

**Pre-registered, scored once. Batch C is spent after this run.**

No ranker, scorer, weight, threshold, label, or frozen artifact was changed. No result was used to tune or rerun scoring.

- Frozen ranker commit: `e6f8da0271f00223346a74ffcf32bb34b54383dd`
- Frozen Batch C artifact SHA-256: `3ab15ab445e00613b1fb7a48e32c94f22f7a03f451182ff2fac5912b3aaa2dc2`
- Provider: `dRPC`
- Verified scoring N: **30**
- Excluded before scoring: **0**
- Scoring passes: **1**

## Trace-run history

An earlier exploratory trace attempt at
`reports/new_batches/batchC/phase2/run_20261018T103347Z` stopped after 23 rows
with `STOPPED_BILLING_PROMPT`. That stop was not reproduced: the final trace
run below completed all 30 rows with `billing_prompt_detected=false` and
`rate_limit_hits=0`. The earlier partial run was not scored and did not affect
the final metrics.

## Metrics

Wilson intervals are two-sided 95% Wilson score intervals.

| Key | R@1 | R@3 | R@5 |
| --- | --- | --- | --- |
| Address + selector (primary) | 3/30 (10.00%; 3.46-25.62%) | 11/30 (36.67%; 21.87-54.49%) | 12/30 (40.00%; 24.59-57.68%) |
| Address-only sensitivity | 5/30 (16.67%; 7.34-33.56%) | 12/30 (40.00%; 24.59-57.68%) | 15/30 (50.00%; 33.15-66.85%) |
| Selector-only sensitivity | 5/30 (16.67%; 7.34-33.56%) | 11/30 (36.67%; 21.87-54.49%) | 13/30 (43.33%; 27.38-60.80%) |

## Pre-scoring exclusions

| Transaction | Incident | Reason |
| --- | --- | --- |
| — | — | None |

Batch C is spent and sealed after this single final scoring pass.
