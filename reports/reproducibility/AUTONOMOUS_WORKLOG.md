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
| AR-002 | 2 | coordinator | DONE | Add a schema-aware offline validator for the bound cohort manifest and explicit admission states | Existing `research_protocol.admit()` and current manifest schemas | `20 passed`; current root manifest audited as 14 accepted, 232 needed, `BLOCKED-BY-DATA`; no frozen artifact changes |
| AR-003 | 7 | coordinator | DONE | Align benchmark Docker image with pinned Python and lockfile | Existing `requirements.lock` | `6 passed`; benchmark image now uses Python 3.11.9 and `requirements.lock` |
| AR-004 | 4 | coordinator | EXTERNALLY_BLOCKED | Complete authenticated 246-row cohort | Independent sources, reviewers, RPC traces, function labels | `accepted_count == 246` only if evidence genuinely supports it |
| AR-005 | 5 | coordinator | EXTERNALLY_BLOCKED | Run paired detector/baseline evaluation | AR-004; balanced trace coverage | Frozen inputs, completed command, confusion matrices |
| AR-006 | 6 | coordinator | BLOCKED | Function-level localization evaluation | Exact function ground truth | New immutable holdout; Batch E unchanged |
| AR-007 | 6 | coordinator | BLOCKED | Revalidate calibration, routing/cost, and HITL claims | Eligible data, provider authorization, human reviewers | Measured outputs or explicit external blocker |
| AR-008 | 7 | coordinator | IN_PROGRESS | Align CI, setup, Docker, and replay documentation | AR-003 | CI, setup, README, and Docker now use the lockfile; replay/tool documentation remains |
| AR-009 | 8 | coordinator | DONE | Produce final claim/evidence ledger and consistency report | All available evidence | `reports/reproducibility/CLAIM_CLOSURE_LEDGER.json`; 31 claims classified with fixed status vocabulary |
| AR-010 | 6 | coordinator | DONE | Add offline calibration/cost evidence audit and reject empty legacy tracker reports as empirical evidence | Existing calibration and cost artifacts; Batch E runtime hash | Audit exits 2 with explicit blocked status; legacy empty flag is overridden by audit semantics; no frozen artifact changes |
| AR-011 | 6 | coordinator | DONE | Reconcile valid cohort versions and identify locally runnable detector/localization work without touching frozen batches | Current manifests, frozen Batch E, comparable trace coverage | Root 14/246; v3 20/246; v4 22/246; detector gate data-blocked; Batch E verifier passes unchanged |

## Execution rules

- Never modify files listed as pre-existing dirty or untracked unless a task
  explicitly owns them.
- Never use target paper metrics to tune an evaluation set.
- Record commands, exit codes, changed files, tests, and unresolved blockers at
  each checkpoint.
- Treat accepted, pending, and excluded as distinct states; missing evidence is
  never silently promoted.

## Checkpoints

### AR-002 — bound cohort manifest validator

- Changed: `benchmark/validate_cohort_manifest.py`,
  `tests/test_cohort_manifest_validator.py`.
- Command: `python -m pytest tests/test_cohort_manifest_validator.py tests/test_research_protocol.py tests/test_authentic_publication.py tests/test_runtime_layout.py -q -p no:cacheprovider`
- Result: exit 0, 20 passed.
- Command: `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .`
- Result: exit 0, manifest internally valid, 14 accepted, 0 pending, 0 excluded,
  target 246, status `BLOCKED-BY-DATA`.
- Commit: `6861508`.
- Reassessment command: `python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v4_20261016/cohort_manifest.json --root .`
- Reassessment result: exit 0, schema 3 internally valid, 22 accepted, 0
  pending, 0 excluded, 224 needed, status `BLOCKED-BY-DATA`; eight chains are
  represented and `not_independent_human_review` remains true.
- Version comparison command: `python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v3_20261016/cohort_manifest.json --root .`.
- Version comparison result: exit 0, schema 3 internally valid, 20 accepted,
  0 pending, 0 excluded, 226 needed, status `BLOCKED-BY-DATA`; v4 adds two
  accepted rows and two represented chains but still does not meet the target.
- Strict gate command: `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root . --strict`
- Strict gate result: exit 2, correctly refuses the incomplete 246-row target.

### AR-003 — benchmark container pinning

- Changed: `Dockerfile.benchmark`, `tests/test_runtime_layout.py`.
- Command: `python -m pytest tests/test_runtime_layout.py tests/test_cohort_manifest_validator.py -q -p no:cacheprovider`
- Result: exit 0, 6 passed.
- Commit: `acf4988`.

### AR-008 — CI alignment partial

- Changed: `.github/workflows/ci.yml`, `tests/test_runtime_layout.py`.
- Command: `python -m pytest tests/test_runtime_layout.py tests/test_cohort_manifest_validator.py -q -p no:cacheprovider`
- Result: exit 0, 7 passed.
- CI now uses Python 3.11.9, `requirements.lock`, and `make test`.
- Remaining AR-008 work: align `setup.py`, README defaults, and replay/tool
  dependency documentation without changing frozen evidence.

### AR-008 — packaging defaults

- Changed: `setup.py`, `README.md`, `tests/test_runtime_layout.py`.
- Initial focused test result: exit 1 because the Windows default text encoding
  could not decode the UTF-8 README; the test was corrected to read UTF-8.
- Final command: `python -m pytest tests/test_runtime_layout.py tests/test_cohort_manifest_validator.py -q -p no:cacheprovider`
- Final result: exit 0, 8 passed.
- `setup.py`, README, CI, and both Docker paths now default to the lockfile and
  Python 3.11.9 where the runtime is declared.
- Packaging smoke check: `python setup.py --name` exited 0 and printed
  `FaultSeeker`.
- Syntax check: `python -m py_compile` over all changed Python modules and tests
  exited 0.

### AR-002 — command surface

- Changed: `Makefile`, `README.md`.
- Intended command: `make validate-cohort`.
- Environment result: exit 127 because `make` is not installed in this Windows
  environment; no installation was attempted.
- Equivalent command: `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .`.
- Equivalent result: exit 0, 14 accepted, target 246, `BLOCKED-BY-DATA`.
- Focused regression command: `python -m pytest tests/test_runtime_layout.py tests/test_cohort_manifest_validator.py -q -p no:cacheprovider`.
- Result: exit 0, 8 passed.

### AR-009 — offline historical reproduction

- Command: `python scripts/reproduce/run_all.py`.
- Result: exit 0; all seven scoped historical metrics passed: F1 0.7586,
  modeled cost saving 35.0%, saved localization top-1 6.1%, reentrancy labels
  17, vulnerability strings 82, cohort rows 231, and chain count 8.
- Interpretation: this independently recalculates saved historical artifacts;
  it does not authenticate the paper cohort or reproduce live empirical quality.

### AR-005 — leakage-free detector gate

- Command: `python benchmark/run_honest_experiments.py --results-dir C:/Users/91701/AppData/Local/Temp/omnirush/faultseeker-honest-audit`.
- Result: exit 2, correctly blocked before emitting comparison tables.
- Recorded coverage: exploit trace features 10/14 (0.71), benign trace features
  1000/1000 (1.00).
- Reason: cross-class comparison would be confounded by feature availability.
- Required next dependency: collect missing trace evidence with an authorized
  trace-capable RPC, then repeat only on a frozen eligible cohort.

### Focused regression sweep

- Detector and honest-evaluation tests: `67 passed` —
  `tests/test_honest_eval.py`, `test_paper_experiments.py`,
  `test_paper_detector.py`, `test_paper_fallback.py`, `test_paper_tiers.py`.
- Calibration/confidence tests: `31 passed` — `test_calibration_schema.py`,
  `test_confidence_scorer.py`.
- Routing/cost tests: `66 passed` — `test_llm_router.py`,
  `test_llm_router_ablation.py`, `test_query_routing.py`,
  `test_cost_tracker_ablation.py`.
- HITL/function-flow tests: `15 passed` — `test_local_control_flow.py`,
  `test_analyst_guidance.py`, `test_function_agent_flow.py`,
  `test_source_analysis_safety.py`.
- RPC/acquisition tests: `14 passed` — `test_rpc_mechanisms.py`,
  `test_paper_rpc_probe.py`, `test_acquisition_paths.py`.
- Storage/replay tests: `17 passed, 7 skipped` —
  `test_storage_normalization.py`, `test_compiled_evm_integration.py`,
  `test_historical_fork_replay.py`; skips are live/optional replay cases.
- Evidence/publication tests: `46 passed` — `test_evidence_manifest.py`,
  `test_claim_registry.py`, `test_cohort_rebuild.py`, `test_cohort_versions.py`,
  `test_authentic_publication.py`.
- These are focused current-revision results, not a completed full-suite result.

### AR-010 — calibration and cost evidence gate

- Changed: `scripts/reproduce/audit_calibration_cost_evidence.py`,
  `tests/test_calibration_cost_evidence_audit.py`,
  `faultseeker/research/cost_tracker.py`,
  `tests/test_cost_tracker_ablation.py`.
- Command: `python scripts/reproduce/audit_calibration_cost_evidence.py --root .`.
- Result: exit 2 by design, status `BLOCKED_EMPIRICAL_EVIDENCE`; the retained
  calibrator is `legacy-unspecified` and non-deployable, the CV artifact has no
  ECE or row-level provenance, and the measured cost run is 0/100 with no calls.
- Modeled cost arithmetic remains 35.0%; the old 58% overall interpretation is
  recorded as removed Tier-2-only arithmetic.
- Regression command: `python -m pytest tests/test_calibration_cost_evidence_audit.py tests/test_cost_tracker_ablation.py -q -p no:cacheprovider`.
- Result: exit 0, 19 passed.
- The legacy `CostTracker` report remains byte-compatible with frozen Batch E;
  the evidence audit classifies an empty report as having no observed runtime
  usage and not qualifying as empirical evidence.

### AR-009 — claim closure scoreboard

- Changed: `scripts/reproduce/claim_closure_ledger.py`,
  `tests/test_claim_closure_ledger.py`,
  `reports/reproducibility/CLAIM_CLOSURE_LEDGER.json`, `README.md`.
- Command: `python scripts/reproduce/claim_closure_ledger.py --root . --write reports/reproducibility/CLAIM_CLOSURE_LEDGER.json`.
- Result: 31 claims classified as 13 `VERIFIED_IMPLEMENTATION`, 4
  `CONTRADICTED_BY_CURRENT_EVIDENCE`, 13 `EXTERNALLY_BLOCKED`, and 1
  `UNVERIFIED`; no empirical claim was marked reproduced.
- Current root cohort: 14 accepted of 246, 232 remaining, six represented
  chains, and `not_independent_human_review=true`.
- Frozen Batch E remains unchanged: n=40, R@1=14/40, R@3=27/40,
  R@5=33/40.

### AR-011 — cohort/version and frozen-batch reconciliation

- Commands: `python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .`,
  the equivalent v3 and v4 commands, and
  `python scripts/research/verify_batch_e_result.py`.
- Results: root manifest 14 accepted / 246 target / 232 remaining; v3 has 20
  accepted / 226 remaining; v4 has 22 accepted / 224 remaining. All three
  manifests are internally valid but `BLOCKED-BY-DATA` and retain
  `not_independent_human_review=true`.
- Detector command: `python benchmark/run_honest_experiments.py --results-dir C:/Users/91701/AppData/Local/Temp/omnirush/faultseeker-honest-audit-current`.
  Exit 2 is correct: exploit trace coverage is 10/14 (0.71) versus benign
  1000/1000 (1.00), so comparison metrics are blocked.
- Frozen Batch E verification: exit 0, `PASS`, R@1=14/40, R@3=27/40,
  R@5=33/40, 122 RPC dispatch records and 323 registry records. An earlier
  verifier failure exposed a cost-tracker runtime-hash drift; the tracker was
  restored to its frozen digest `0da7c83f...` without changing Batch E files,
  and verification now passes.

### Current full-suite checkpoint

- Command: `python -m pytest tests -x -q -p no:cacheprovider`.
- Result: 965 passed, 7 skipped before the first failure at
  `tests/test_t3_evidence_audits.py::test_local_source_audit_is_network_free_and_keeps_adjudication_separate`.
- Failure: the pre-existing dirty local-source evidence snapshot reports
  `unresolved_rows_attempted=69`, while the test requires at least 70. The
  modified artifacts are outside this workstream and were not changed.
- The initial non-`-x` full-suite attempt exceeded 120 seconds after reaching
  the same failure region; it is not treated as a pass.
- Focused current-revision suite for this mission remains passing: 36 tests,
  including calibration/cost audit, ledger, schema, measured-cost, and frozen
  Batch E runtime checks.
