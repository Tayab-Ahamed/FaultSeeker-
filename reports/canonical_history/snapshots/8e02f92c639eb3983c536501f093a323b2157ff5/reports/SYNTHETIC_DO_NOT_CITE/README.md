# ⚠️ SYNTHETIC RESULTS — DO NOT CITE

**These files must NOT be used in any paper, submission, or public report.**

## Why This Directory Exists

The `run_eval.py` harness in `benchmark/` uses proxy-scoring functions that internally read ground-truth labels to simulate baselines (Static proxy, Dynamic trace-rule, LLM-only). This produces numerically plausible output quickly — useful for verifying the pipeline structure and table-generation scripts — but the results are **not produced by running the actual tools on real transactions**.

## What's In Here

| File | Content | Status |
|---|---|---|
| `baseline_comparison.csv` | Proxy-scored baseline table | **SYNTHETIC — not real** |
| `ablation_results.csv` | Proxy-scored ablation table | **SYNTHETIC — not real** |
| `adversarial_robustness.csv` | Proxy-scored adversarial table | **SYNTHETIC — not real** |
| `summary.json` | Summary of proxy results | **SYNTHETIC — not real** |
| `research_tables.tex` | LaTeX tables from proxy data | **SYNTHETIC — not real** |

## Where The Real Results Are

The paper-cited results are in **`reports/research_results/`**, which contains:

- `baseline_comparison.csv` → Table 4 (11,059 transactions, paper §6.3)
- `ablation_results.csv` → Table 5 (paper §6.4)
- `adversarial_robustness.csv` → Table 6 (paper §6.5)
- `reentrancy_metrics.json` → Section 6.6
- `runtime_cost.json` → Section 6.7
- `summary.json` → All headline numbers (F1=0.969, FPR=0.003)

## How to Regenerate Real Results

```bash
python benchmark/run_honest_experiments.py
python benchmark/run_adversarial_eval.py
```

These require RPC access and API keys. See `benchmark/README.md`.
