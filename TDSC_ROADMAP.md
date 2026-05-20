# TDSC Research Roadmap

This roadmap keeps the project focused on becoming a rigorous security research system instead of a broad engineering demo.

## Primary Research Claim

FaultSeeker++ should evolve toward a dependable adaptive blockchain exploit localization framework with calibrated confidence and adversarial robustness.

## Phase 1: Stabilize the Research Platform

- Keep CLI behavior, README commands, package metadata, and benchmark scripts aligned.
- Preserve deterministic outputs for benchmark and regression runs.
- Track failure states explicitly, especially empty function inspection, trace collection failure, proxy-heavy traces, and low-confidence evidence cards.

## Phase 2: Adaptive Failure-Aware Forensics

- Add a controller that detects weak analysis states such as `functions_to_inspect_count == 0`.
- Trigger fallback strategies: graph expansion, aggressive call-depth inspection, proxy unwrapping, state-delta reasoning, and entropy-based trace analysis.
- Report which fallback mode activated and whether it improved localization.

## Phase 3: Learned Confidence Calibration

- Replace fixed confidence weights with a trained calibration model.
- Candidate features: pattern-match score, code-evidence score, transaction-consistency score, LLM confidence, trace entropy, call depth, state delta, and token-flow anomaly score.
- Report Expected Calibration Error, Brier score, reliability diagrams, and confidence intervals.

## Phase 4: Benchmark Rigor

- Add benign DeFi transactions for false-positive measurement.
- Stage the Hugging Face Ethereum activity non-scam-address sample through `benchmark/import_hf_ethereum_activity.py`, then validate with `benchmark/validate_benign_dataset.py`.
- Resolve the 293 DeFiHackLabs transaction candidates and rug-pull contract incidents before increasing the verified exploit benchmark count.
- Compare against static and dynamic baselines where reproducible: Slither, Mythril, Securify, TxSpector-style trace rules, and DAppFL-style localization.
- Add ablations for adaptive fallback, graph reasoning, learned calibration, and human-in-the-loop review.

## Phase 5: Security and Dependability Evaluation

- Define attacker capability, trust assumptions, RPC/provider assumptions, and failure assumptions.
- Evaluate robustness against proxy obfuscation, misleading function names, fake events, recursive noise traces, multi-transaction splitting, and prompt-injection-like calldata.
- Publish reproducible scripts, fixed seeds, dataset labels, and environment instructions.
