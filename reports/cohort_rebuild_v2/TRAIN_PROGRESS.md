# Train-only research checkpoint

Run: `20261015T140915-334cd54a`. Reproduce with `python scripts/run_authentic_research.py`.
Exact implementation files, hashes, seed, frozen split digest, raw detector
observations, per-variant coverage and failure details are in the run directory.
Every dispatch and variant outcome is recorded in `experiments_log.json`.

The frozen train population is ten accepted exploits. Seven have accepted call
traces, including the newly recovered Beanstalk creation transaction. BSC failed
the chain-ID request; Fantom and Gnosis debug methods returned transaction-not-found.
The request records are in `trace_acquisition_train.json`: 65 outbound logical RPC
requests, conservatively allocated $0.000390. No model inference was dispatched.

Structural reentrancy: TP=3 FP=1 FN=0 TN=3, precision=0.75, recall=1,
F1=0.8571428571428571. Repeated-address baseline: TP=3 FP=4 FN=0 TN=0,
precision=0.42857142857142855, recall=1, F1=0.6. These are observed component
results on seven available train traces. The three missing cases are not negatives.

The structural error is Beanstalk: actual recursion exists in the execution tree,
but its adjudicated root cause is governance manipulation rather than reentrancy.
Without ordered storage evidence, structural recursion alone cannot establish a
state hazard. No weight, tier boundary, threshold, label or frozen split was changed.

Full storage-aware detector: unscored; no accepted opcode capture on this cohort.
Overall system F1, paired billed cost savings, function localization and Table VI
remain unmeasured. No component result substitutes for those measurements.
The held-out file was not loaded and the one-use final exam was not dispatched.

Next evidence work: canonical replay on train identities, with the same receipt,
block-environment, transaction-prefix and storage-ownership acceptance checks.
