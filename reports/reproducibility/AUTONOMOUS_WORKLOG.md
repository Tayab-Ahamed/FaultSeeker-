# FaultSeeker++ Autonomous Research Worklog

This worklog records bounded execution checkpoints for the autonomous research
completion directive. It does not replace frozen batch manifests, claim-closure
reports, or provenance evidence.

## Baseline checkpoint

- Branch: `localization-continuous-merge`
- HEAD: `fec6fbf95707d3af57b2641de0d36af29eca386d`
- Baseline captured: 2026-10-19 (Asia/Calcutta)
- Frozen research batches: Batch B, Batch C, Batch D, and Batch E are preserved;
  no rerun, retune, or rescore is permitted without a new task.
- Working tree: pre-existing modified and untracked evidence/research artifacts
  are preserved and are not owned by this worklog.
- Current cohort reference: `benchmark/cohort_manifest.json` reports target 246,
  accepted 14, remaining 232, and `not_independent_human_review: true`.
- Batch E reference: `reports/new_batches/batchE/scoring.json` records one
  address-only score over 40 rows: R@1 14/40, R@3 27/40, R@5 33/40.

## Task ledger

| ID | Priority | Owner | Status | Objective | Dependencies | Acceptance evidence |
|---|---:|---|---|---|---|---|
| AR-001 | 0 | coordinator | DONE | Preserve live Git state and frozen evidence references | None | Baseline above; no destructive Git command used |
| AR-002 | 2 | coordinator | READY | Add a schema-aware offline validator for the bound cohort manifest and explicit admission states | Existing `research_protocol.admit()` and current manifest schemas | Focused validator tests; no frozen artifact changes |
| AR-003 | 7 | coordinator | READY | Align benchmark Docker image with pinned Python and lockfile | Existing `requirements.lock` | Focused runtime-layout test; only Docker/test files changed |
| AR-004 | 4 | coordinator | BLOCKED | Complete authenticated 246-row cohort | Independent sources, reviewers, RPC traces, function labels | `accepted_count == 246` only if evidence genuinely supports it |
| AR-005 | 5 | coordinator | BLOCKED | Run paired detector/baseline evaluation | AR-004 | Frozen inputs, completed command, confusion matrices |
| AR-006 | 6 | coordinator | BLOCKED | Function-level localization evaluation | Exact function ground truth | New immutable holdout; Batch E unchanged |
| AR-007 | 6 | coordinator | BLOCKED | Revalidate calibration, routing/cost, and HITL claims | Eligible data, provider authorization, human reviewers | Measured outputs or explicit external blocker |
| AR-008 | 7 | coordinator | READY | Align CI, setup, Docker, and replay documentation | AR-003 | Current commands and environment records agree |
| AR-009 | 8 | coordinator | READY | Produce final claim/evidence ledger and consistency report | All available evidence | Every material claim classified honestly |

## Execution rules

- Never modify files listed as pre-existing dirty or untracked unless a task
  explicitly owns them.
- Never use target paper metrics to tune an evaluation set.
- Record commands, exit codes, changed files, tests, and unresolved blockers at
  each checkpoint.
- Treat accepted, pending, and excluded as distinct states; missing evidence is
  never silently promoted.
