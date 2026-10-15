# Evaluation Protocol

## Core Metrics

- Precision, recall, F1, false-positive rate, and false-negative rate.
- Runtime per transaction, trace collection latency, memory use, token cost, and cloud/local routing counts.
- Confidence quality: Brier score, Expected Calibration Error, and reliability bins.

## Dataset Splits

- Exploit set: current curated exploit benchmark plus verified public incident sources.
- Benign set: normal DeFi swaps, staking, governance votes, liquidations, arbitrage, and transfers. The current reproducible staging path is `benchmark/import_hf_ethereum_activity.py`, which imports non-scam-address Ethereum transaction candidates for false-positive testing.
- Temporal split: train/calibrate on earlier years, test on later years.
- Cross-chain split: hold out at least one chain profile for generalization testing.

## Baselines

- Static analysis: Slither, Mythril, Securify where source code exists.
- Dynamic/trace systems: TxSpector-style trace rules and DAppFL-style localization.
- LLM-only baseline: same prompts without deterministic signals, graph features, or adaptive fallback.
- External baseline outputs must be normalized with `benchmark/ingest_external_baselines.py`; proxy baselines are only for reproducible local sanity checks.

## Statistical Tests

- Bootstrap confidence intervals for F1, runtime, and cost.
- Paired t-test and Wilcoxon signed-rank test for paired metric deltas.
- McNemar test for paired classification correctness.

## Ablations

- Full system.
- Without FAEGL failure-aware localization.
- Without adaptive fallback.
- Without graph/TIG features.
- Without learned calibration.
- Without HITL feedback.
- Without LLM routing.

## Reproducibility

- Run `python benchmark/prepare_research_dataset.py` to generate the expansion manifest.
- Run `python benchmark/import_hf_ethereum_activity.py --target-rows 10000` to stage the current benign candidate set.
- Run `python benchmark/run_research_experiments.py` to generate baseline, ablation, adversarial robustness, and LaTeX result tables under `reports/research_results/`.
- Run `python benchmark/ingest_external_baselines.py --make-template` to create the Slither/Mythril/TxSpector/GPTScan result sheet, then rerun it with `--input` after the tools have produced predictions.
- Run `python benchmark/analyze_explainability_study.py --input docs/research/human_study_response_template.csv` to validate the human-study analysis path.
- Run `python benchmark/import_rugpull_contracts.py` to stage contract-level rug-pull incident metadata.
- Run `python benchmark/run_eval.py --signals-only --limit 50` for a cached signal smoke test.
- Run `python -m pytest tests -q -p no:cacheprovider` for deterministic local regression.
