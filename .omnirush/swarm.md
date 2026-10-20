# Goal
Raise FaultSeeker++ function-level localization using only the 110-row development set for grouped 5-fold out-of-fold evaluation, then seal and score a fresh Batch D exactly once.
Batch B and Batch C are spent and must not be read for tuning or rescored; frozen baseline commit e6f8da0 remains untouched.

## Tasks
| id | task | owner | status | result |
|---|---|---|---|---|
| T1 | Lane A call-path features and grouped OOF evaluation | lane-a | running | pending |
| T2 | Lane B selector/storage matching and grouped OOF evaluation | lane-b | running | pending |
| T3 | Lane C learned reranker inside grouped CV | lane-c | running | pending |
| T4 | Lane D candidate-generation fixes and grouped OOF evaluation | lane-d | running | pending |
| T5 | Merge helpful lanes, seal Batch D, score once, report | merge | todo | pending |

## Findings

## Decisions
- Branch every lane from ranker-upgrades-20261017; do not modify frozen e6f8da0.
- Use only the 110-row set for development; grouped folds must keep incident and contract groups together.
- Never read Batch B or Batch C per-row results; never rescore or tune on them.
- Do not edit paper, README, or unrelated number files; never push or commit main.
- Free-tier RPC only; never print or persist credentials; stop on billing or quota exhaustion.
