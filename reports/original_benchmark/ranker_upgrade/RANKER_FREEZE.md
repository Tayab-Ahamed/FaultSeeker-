# Ranker development freeze

**Status:** frozen before any Batch C work

## Frozen code

- Branch: `ranker-upgrades-20261017`
- Code commit: `e6f8da0271f00223346a74ffcf32bb34b54383dd`
- Short hash: `e6f8da0`
- Commit subject: `test: consolidate ranker ordering checks`
- Ranker implementation: `faultseeker/function_analysis/function_ranker.py`
- Scorer fix preserved: `70d1b09`

The frozen ranker order is:

1. call-path concentration descending, where concentration is observed count divided by distinct caller-path prefixes;
2. terminal fan-out ascending;
3. maximum supporting call depth descending;
4. raw observed count descending;
5. stable candidate encounter order.

## Evaluation boundary

Development used only the saved original 110-row population and its fixed 90/20
development/holdout split. No Batch A, Batch B, or Batch C artifact was used for
tuning or evaluation. No RPC, tracing, paid service, push, or paper edit was
performed.

The stored scorer baseline remains `25/110`, `49/110`, `52/110` (22.73% / 44.55%
/ 47.27%). The final ranker measurements are separate offline reranking
measurements and must not be substituted for that scorer baseline.

## Final measurements

Primary address-plus-function metric:

| Population | R@1 | R@3 | R@5 |
| --- | ---: | ---: | ---: |
| Original 110 | 40/110 | 55/110 | 58/110 |
| Development 90 | 33/90 | 45/90 | 48/90 |
| Holdout 20 | 7/20 | 10/20 | 10/20 |

Verification: `python -m pytest tests -q -p no:cacheprovider` → **996 passed,
7 skipped**.

Batch C remains sealed. No tracing or scoring may begin until a later step
explicitly opens that phase.
