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
| AR-008 | 7 | coordinator | DONE | Align CI, setup, Docker, and replay documentation | AR-003 | CI, setup, README, Docker, and `docs/PAPER_REPRODUCTION.md` use the pinned workflow; Docker execution remains environment-blocked |
| AR-009 | 8 | coordinator | DONE | Produce final claim/evidence ledger and consistency report | All available evidence | `reports/reproducibility/CLAIM_CLOSURE_LEDGER.json`; 31 claims classified with fixed status vocabulary |
| AR-010 | 6 | coordinator | DONE | Add offline calibration/cost evidence audit and reject empty legacy tracker reports as empirical evidence | Existing calibration and cost artifacts; Batch E runtime hash | Audit exits 2 with explicit blocked status; legacy empty flag is overridden by audit semantics; no frozen artifact changes |
| AR-011 | 6 | coordinator | DONE | Reconcile valid cohort versions and identify locally runnable detector/localization work without touching frozen batches | Current manifests, frozen Batch E, comparable trace coverage | Root 14/246; v3 20/246; v4 22/246; detector gate data-blocked; Batch E verifier passes unchanged |
| AR-012 | 5 | coordinator | DONE | Diagnose current full-suite source-audit mismatch and publish minimum external evidence acquisition requirements | Dirty source-resolution artifacts; claim ledger | Mismatch is stale/inconsistent evidence: current CSV has 69 unresolved rows while dirty summary claims 72; no rows or adjudications fabricated; acquisition plan committed |
| AR-013 | 5 | coordinator | DONE | Make the current manuscript evidence-bounded and assemble a submission artifact package | Claim ledger, retained reports, paper source | Unsupported result tables removed/replaced; manuscript map, reproduction guide, evidence manifest, and final verification report added |

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

### AR-012 — source-audit diagnosis and acquisition plan

- Reproduction command: `python -m pytest tests/test_t3_evidence_audits.py::test_local_source_audit_is_network_free_and_keeps_adjudication_separate -q -p no:cacheprovider`.
- Current result: exit 1 because `local_source_resolution_audit.audit()` counts
  69 `UNRESOLVED` rows in the dirty `source_resolution_audit.csv`, below the
  test's committed 70-row floor. The dirty summary claims 72 attempted rows,
  so the summary is stale/inconsistent with its input; the implementation is
  correctly counting the input rather than trusting the summary.
- Exact source-audit diff: row 111 only, transaction
  `0x1a7ee0a7efc70ed7429edef069a1dd001fbff378748d91f17ab1876dc6d10392`, changed
  from `[403]/UNRESOLVED` to `[200]/RESOLVED`. The retained provenance metadata
  `reports/provenance_hunt/http/f3c6feba6f2bbc363a1db8cd2b63d84f10cd7eda7a0041ecec912b625a45d823.json`
  records only the earlier 403 response; no retained artifact substantiates the
  dirty 200 result. It remains unverified.
- The dirty local audit also contains stale extra rows 94 and 171. Re-running
  from the current dirty CSV produces 69 rows / 71 URLs, while the dirty
  derived files contain 74 rows and claim 72/74. Clean HEAD produces the
  original 70 rows / 72 URLs. The derived artifacts cannot be regenerated
  reproducibly from the current dirty input.
- Forensic backup created outside the project at
  `C:/Users/91701/AppData/Local/Temp/omnirush/faultseeker-source-audit-forensic-20261019-7cc7e873`.
  Backup hashes: local CSV
  `0e6bdfc6c450646e5a4d6c55445bbc32abe713eb32baa6b92404662146168283`, summary
  `027ed444298c4e2c80b81a6f37c901b1e22f5f1544c1eaddb8f8d3f8c1342c83`.
- Safe regeneration was performed only in temporary output directory
  `C:/Users/91701/AppData/Local/Temp/omnirush/faultseeker-source-audit-regenerated-20261019-7cc7e873`.
  It produced 69 unresolved rows and 71 URLs, with no stale rows 94/171;
  regenerated hashes are CSV `8747e09c44e75cf5d2b47731666eb68bccd18ed747ea876d89c7c838fe11c2f5`
  and summary `5f16d96fc9e00379889b5dde08ecd149a3b0dcbc43d5a5cbcb5e3609332347d4`.
  No tracked evidence file changed.
- No safe local fix exists without restoring a hash-bound evidence snapshot or
  changing the historical assertion. No dirty evidence file was modified and
  no source resolution/adjudication was fabricated.
- Added: `reports/reproducibility/EXTERNAL_EVIDENCE_ACQUISITION_PLAN.md` and
  ledger fields for resolution mode, minimum artifact, and objective acceptance
  criteria for every claim.

### AR-013 — evidence-bounded submission package

- Revised: `paper/blockchain_exploit_forensics_survey_ieee.tex`.
- Removed the unsupported 0.969 headline detector and ablation tables, the
  unsupported population-level dataset wording, and the unsupported calibrated
  probability implication. Replaced them with an evidence-bounded artifact
  table containing only the retained F1=0.7586 proxy aggregate, historical
  7/115 localization summary, frozen Batch E address-only metrics, and 35%
  modeled cost arithmetic.
- Added: `reports/reproducibility/MANUSCRIPT_CLAIM_MAP.md`,
  `SUBMISSION_REPRODUCTION_GUIDE.md`, `SUBMISSION_EVIDENCE_MANIFEST.json`, and
  `SUBMISSION_FINAL_VERIFICATION.md`.
- `python scripts/reproduce/run_all.py`: all seven retained historical metrics
  PASS (F1 0.7586, modeled cost 35.0%, localization 6.1%, labels 17/82,
  cohort rows 231, chains 8).
- `pdflatex` was unavailable, so PDF compilation remains an environment gap;
  label/reference text checks found no removed-table references.
- Regenerated `CLAIM_CLOSURE_LEDGER.json` at commit `c0b039d` and refreshed its
  evidence-manifest hash.
- Final paper disposition: `PAPER CLAIMS PARTIALLY CLOSED — EXTERNAL EVIDENCE REQUIRED`.

### AR-014 — final submission validation

- Continued from commit `b2d86cb`; all unrelated dirty/untracked files and frozen
  research artifacts remained untouched.
- Submission source: `paper/blockchain_exploit_forensics_survey_ieee.tex`, an
  IEEEtran `conference` manuscript. It contains one embedded TikZ figure, four
  embedded tables, an 11-entry inline `thebibliography`, and no external
  `\\includegraphics`, `\\input`, or `\\include` files. No supplementary file
  is referenced by the manuscript. `paper/WORD_COUNT.txt` is the associated
  source accounting file.
- Static package/claim check: exit 0. All 12 citation keys resolve to the 11
  inline bibliography entries; all three `\\ref` targets resolve; five labels
  are unique; retained values and withdrawn headline values were checked; no
  external figures or TeX inputs are required.
- Quantitative claims were checked against the claim map, ledger, and manifest:
  F1=0.7586 is a historical proxy aggregate over 1,231 represented rows;
  localization is historical 7/115 top-1; Batch E is frozen address-only
  14/40, 27/40, 33/40; routing cost is modeled 35% ($0.039/$0.060), not
  measured. No independent validation or completed paper-scale experiment is
  implied.
- Manifest hash check: exit 0, `PASS`.
- Batch E verifier: exit 0, `PASS`; R@1=14/40, R@3=27/40, R@5=33/40.
- Focused validation suite: exit 0, `19 passed`.
- Full suite remains intentionally visible and non-passing: exit 1 after 965
  passed and 7 skipped at the known source-audit failure
  `unresolved_rows_attempted=69` versus the historical floor of 70. No row was
  fabricated, disputed evidence changed, or assertion weakened.
- PDF build outcome: **BLOCKED**. No project TeX compiler was available:
  `pdflatex`, `latexmk`, `xelatex`, `lualatex`, `tectonic`, `bibtex`, and
  `biber` were all unavailable. Therefore no PDF was produced and no technical
  PDF compilation claim is made. The source-level checks above do not replace
  compilation.
- Submission package files: the revised `.tex` source, `paper/WORD_COUNT.txt`,
  `reports/reproducibility/CLAIM_CLOSURE_LEDGER.json`,
  `MANUSCRIPT_CLAIM_MAP.md`, `EXTERNAL_EVIDENCE_ACQUISITION_PLAN.md`,
  `SUBMISSION_REPRODUCTION_GUIDE.md`, `SUBMISSION_FINAL_VERIFICATION.md`, and
  `SUBMISSION_EVIDENCE_MANIFEST.json`. Scientific status remains
  `PARTIALLY_CLOSED_EXTERNAL_EVIDENCE_REQUIRED`.
- Final status: `SUBMISSION PACKAGE BLOCKED` because the essential PDF artifact
  could not be compiled in the available environment; technical source checks
  pass, but external empirical requirements remain unsatisfied.

### AR-015 — recover original targets and fix localization serialization

- Recovered the original target specification from the historical claim audit at
  `50853e461b635bc1e2cc088b91957cdac2a610d2`, the original paper snapshot at
  `6282729ce34bd4a17cc99e750d23ad383ff4b0c1`, the baseline/ablation/human-study
  protocols, and `benchmark/claim_registry.py`.
- Added the authoritative target tracker:
  `reports/reproducibility/ORIGINAL_CLAIM_MISSION.json`. It records the original
  detector, reentrancy, 246-row cohort, ten-chain/label, paired-baseline, cost,
  benign-prefilter, WAF, localization/guidance, calibration, adversarial,
  human-study, and reproducibility targets with acceptance criteria, current
  baselines, dependencies, evidence, status, and next actions.
- Found a real localization adapter defect in
  `benchmark/generate_pipeline_predictions.py`: it reconstructed ranked
  candidates with `split("_")`, truncating function names containing underscores
  and discarding the ranker's explicit identity/rank metadata. The adapter now
  consumes `FunctionRanker.ranked_functions` and retains `code_address`,
  function, rank, selector, and supporting depth information; the legacy path
  uses `rsplit`.
- Added regression coverage in
  `tests/test_pipeline_prediction_serialization.py` for explicit rank metadata
  and underscore-containing function labels.
- Targeted verification: exit 0, `10 passed`:
  `python -m pytest tests/test_pipeline_prediction_serialization.py tests/test_explicit_function_rank_order.py tests/test_ranker_pattern_integrity.py -q -p no:cacheprovider`.
- An initial broader command named nonexistent `tests/test_function_ranker.py`
  and exited 4; it was corrected without changing source or evidence.
- The current honest detector run remains data-blocked at 10/14 accepted exploit
  rows with trace features versus 1000/1000 benign rows; no incomparable output
  was promoted. Frozen Batch E and unrelated dirty/untracked files remain
  untouched.
- Implementation status: serializer fix completed. Empirical targets remain
  blocked by missing authenticated data, independent review, provider/WAF
  authorization, human responses, and clean Linux/TeX build resources.

### AR-016 — current data readiness checkpoint

- `python benchmark/validate_dataset.py`: exit 1. The current strict input has
  14 unique valid hashes across six chains, below the validator's 160+ local
  target. This confirms the original 246-row target cannot be evaluated from
  the current strict CSV without new legitimate admissions.
- `python benchmark/validate_benign_dataset.py --input benchmark/imported/hf_ethereum_benign_transactions.csv`:
  exit 0; 10,000 rows, zero duplicate hashes, required fields present. These
  are Ethereum non-scam-address candidates, not independently verified benign
  DeFi ground truth for the original prefilter claim.
- `python benchmark/run_honest_experiments.py --results-dir <temporary>`:
  exit 2; comparison blocked at 10/14 exploit trace-feature coverage versus
  1000/1000 benign trace rows. No incomparable metrics were promoted.
- Expanded implementation regression after the serializer fix: exit 0,
  `36 passed` across the prediction adapter, rank ordering, pattern integrity,
  and function-selection safety tests.
- This checkpoint advances data readiness once and does not alter the known
  source-audit mismatch or any frozen/unrelated artifact.

### AR-017 — localization serializer before/after validation

- Added `scripts/research/compare_localization_serializer.py`, a read-only
  comparison harness that reproduces the pre-fix `split("_")` adapter and runs
  the corrected serializer on saved candidate outputs. It performs no ranker,
  RPC, provider, scoring, Batch E, or Batch D rerun.
- Batch D saved candidates: 10 files / 560 candidates. The saved selectors had
  no underscore-containing human function names, so old and new identity counts
  were both 560/560 and no top-k result can be inferred from this adapter-only
  comparison.
- Provider-pinned saved outputs: 115 files / 1,091 candidates, 114 rows with
  valid original function-level ground truth. Old serializer exact identities:
  1,088/1,091; corrected serializer: 1,091/1,091; three candidate positions
  changed in one transaction because `add_liquidity` was previously split into
  address=`liquidity`, function=`add`. The corrected output preserves the full
  function/address identity and rank metadata.
- Function-level top-k on the same saved outputs was unchanged: old and new
  Top-1/Top-3/Top-5 were respectively 24/114, 48/114, and 51/114. This is a
  valid before/after adapter result, not a new generalization estimate and not
  evidence that the original localization target was achieved.
- Retained artifacts:
  `reports/reproducibility/LOCALIZATION_SERIALIZER_COMPARISON.json` and
  `LOCALIZATION_SERIALIZER_COMPARISON_PROVIDER_PINNED_ALL.json`, including
  input hashes, row-level old/new identity counts, ground-truth availability,
  and explicit no-rerun scope.
- Regression verification after the nested-depth metadata fix: exit 0,
  `36 passed` with the targeted localization/function-selection suite.
- T09 is now `implemented_not_validated`: the local adapter defect is fixed and
  measured, but the original live/held-out model-assisted localization and
  guidance requirements remain unvalidated.
