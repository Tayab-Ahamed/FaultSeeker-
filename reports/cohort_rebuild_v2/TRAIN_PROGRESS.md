# Train-only research checkpoint

Three genuine component invocations are recorded in experiments_log.json. Latest:
`20261015T143221-eb779fdb`. Reproduce with `python scripts/run_authentic_research.py`.
Each run preserves config, seed, system hashes, raw predictions, explicit coverage
and exact compressed source bytes. No threshold, weight, frozen membership or
held-out outcome has been used for tuning.

Frozen train: ten source-adjudicated exploits; call coverage seven; opcode coverage
two. Missing observations stay missing. Structural: TP=3 FP=1 FN=0 TN=3,
precision 0.75, recall 1.0, F1 0.8571428571428571. Repeated-address: TP=3 FP=4
FN=0 TN=0, precision 0.42857142857142855, recall 1.0, F1 0.6.

Full storage detector on Rubic and Euler only: TP=0 FP=1 FN=0 TN=1,
precision 0.0, recall undefined (no positives), F1 0.0. This is not an estimate of
reentrancy sensitivity, not the paper Table V cohort and not overall system F1.
The full-positive coverage gap is being addressed through Revest canonical-prefix
replay. The held-out file has not been loaded and no exam permit is consumed.

Failure analysis: structural-only Beanstalk recursion is not its adjudicated
root cause. Full-detector Euler falsely marks sequential DAI calls at different
depths as nested slot rewrites. All four implicated slot groups have zero actual
ancestor/descendant write-frame pairs. Fixing that semantics is the next train
iteration; it does not require changing paper weights or classification thresholds.

New replay request counts, source hashes and honest capability limitations are in
RPC_TRAIN_CONCLUSION.json. Overall system F1, paired billed inference savings,
source-linked localization and Table VI remain unmeasured. No component statistic
substitutes for them. Claim 13 remains UNVERIFIABLE at the paper's full scope.
