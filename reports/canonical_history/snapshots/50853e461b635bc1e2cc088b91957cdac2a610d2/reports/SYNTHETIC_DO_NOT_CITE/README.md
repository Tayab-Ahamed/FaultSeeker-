# SYNTHETIC OUTPUT - DO NOT CITE

Every file in this directory was produced by `benchmark/run_research_experiments.py`,
whose scoring functions read the ground-truth `label` column directly:

```python
def faegl_score(row):
    if row["label"] == 0:          # <-- reads the answer
        return 0.53 if hash_bucket(row, 307) == 0 else 0.02
    base = 0.66 + type_bonus + ...
```

Consequences:

* The reported F1 (0.9687) is an arithmetic restatement of the labels, not a
  measurement of FaultSeeker++. The `faultseeker/` package is never imported by
  that harness: no transaction is replayed, no trace is collected, no LLM is
  called, no interaction graph is built.
* The ablation rows are the full-system score minus a constant
  (`faegl_score(row) - 0.19`), so they do not measure disabling a component.
* The adversarial deltas are the literal constants written into the analyzer
  closure, evaluated against a two-node hardcoded `synthetic_trace()`.
* `f1_ci_low` (0.9798) exceeds the point estimate (0.9687) because the bootstrap
  resampled per-chain F1 values rather than the pooled metric.

These numbers must not appear in any paper, thesis, or slide deck.
Use `reports/honest_results/` instead, produced by
`benchmark/run_honest_experiments.py`.
