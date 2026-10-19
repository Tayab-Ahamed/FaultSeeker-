# Batch D raw-output report

Single scoring pass; frozen source-backed convenience sample. No independent root-cause adjudication is inferred.

| Match | R@1 | R@3 | R@5 |
|---|---|---|---|
| address_only_sensitivity | 4/10 (40.0%; Wilson95% 16.82–68.73%) | 6/10 (60.0%; Wilson95% 31.27–83.18%) | 6/10 (60.0%; Wilson95% 31.27–83.18%) |
| address_selector_primary | 2/10 (20.0%; Wilson95% 5.67–50.98%) | 3/10 (30.0%; Wilson95% 10.78–60.32%) | 4/10 (40.0%; Wilson95% 16.82–68.73%) |
| selector_only_sensitivity | 2/10 (20.0%; Wilson95% 5.67–50.98%) | 3/10 (30.0%; Wilson95% 10.78–60.32%) | 4/10 (40.0%; Wilson95% 16.82–68.73%) |

| Check | Result |
|---|---:|
| Frozen / RPC-verified rows | 10 / 10 |
| Scoring passes | 1 |
| RPC requests | 40 |
| Billing prompts / rate limits / exclusions | 0 / 0 / 0 |
| LLM calls / commits / pushes | 0 / 0 / 0 |
| Full suite passed / skipped | 1019 / 1 |
| Paid-spend estimate, free-tier only | $0 |

Actual billing was not independently checked. The shared spend ledger remained unchanged during the final full suite. Initial restricted-sandbox test failures were localhost/temporary-path permission errors; the final suite used localhost access and a short workspace temp path, without changing those tests.

## Evaluator review

| Lane | Baseline @1/3/5 | OOF @1/3/5 | Adopted |
|---|---|---|---:|
| B | 40/55/58 | 40/55/58 | 0 |
| C | 25/49/52 | 24/49/54 | 0 |
| D, corrected against production | 40/55/58 | 40/56/58 | 1 |
| D, 109 unique sensitivity | 39/54/57 | 39/55/57 | 1 |

B rejected: zero incremental gain and target-conditioned evidence acquisition. C rejected: primary regression on advertised population. D retained after parser/fold/selector fixes; +1@3 survives deduplication. Historical upstream ranker tuning remains exploratory. These OOF numbers are development evidence, not independent generalization estimates.

## Frozen artifacts

- Batch canonical SHA-256: `e349997c875542ffb85a2205dbc4357e31d547c7dffb3cf1f12aebf3634becf7`
- Scoring bytes SHA-256: `fcb1ffaa1ab99e4123713b378bb3cdf3c6e82c871c7a79f7efec8d8111f5066a`
- Code, public model-cache and configuration pins: `freeze.json` (94 files).
- Row sources, exact quotes, cached-body hashes and exclusions: `draft_source_rows.json` and `batchD_candidates.json`.
- Raw transaction/receipt/callTracer responses: `phase2/raw/*.json`.
- Every dispatched method: `phase2/requests.jsonl`.
- Per-transaction ranked candidates: `phase2/candidates/*.json`.
- All raw ranks, denominator and intervals: `phase2/scoring.json`.
- Machine review: `LANE_REVIEW.json`; machine final: `FINAL_SUMMARY.json`.

## Executed commands

```powershell
python scripts/research/batchD_phase2.py freeze
python scripts/research/batchD_phase2.py collect
python scripts/research/batchD_phase2.py score
```

These commands were executed in that order. Freeze/collection/scoring now refuse to overwrite or score again. Do not rerun this batch as a new test. No paper edits, no main-branch changes, no commits, no pushes. The D adapter is adopted in this frozen research runner; the existing CLI FunctionRanker file is unchanged.
