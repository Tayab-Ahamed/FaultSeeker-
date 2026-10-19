# Evidence recovery and reproducibility closeout

Date: 2026-10-19  
Repository revision at inspection: `427ccc83039e8fad09593c97bed5c8964c5f6c2f`

This closeout records the final local evidence pass after commits `f882455` and
`427ccc8`. It preserves the unrelated dirty and untracked workspace files and
does not modify, rescore, or retune frozen Batch D or Batch E.

## Evidence search performed

The following retained artifacts were inspected and cross-checked against their
manifests, hashes, row identities, and declared admission scope:

- `benchmark/cohort_manifest.json`: root population is 14 accepted of a 246-row
  target; 232 additional accepted records are still required. The manifest
  validates, but explicitly reports `BLOCKED-BY-DATA` and no independent human
  review.
- `benchmark/versions/cohort_v3_20261016/cohort_manifest.json`: 20 accepted of
  246; 226 additional accepted records are still required.
- `benchmark/versions/cohort_v4_20261016/cohort_manifest.json`: 22 accepted of
  246; 224 additional accepted records are still required. Root and v4 remain
  separate populations.
- `reports/provenance_hunt/FINAL_REPORT.md`, `hunt.json`, `source_manifest.json`,
  `cohort/row_decisions.json`, and provider inventories: all 231 exact legacy
  identities were searched; 15 additional transaction references were found,
  but their paper membership and labels are unproven. No original predictions,
  scorer/configuration, complete baseline outputs, or original model
  transcripts were recovered.
- `reports/external_runs/phase1/*manifest.json` and
  `reports/external_runs/phase2/20261017T011500Z/drpc/manifest.json`: retained
  provider observations are partial conformance and failed/blocked on opcode
  or free-plan/rpc limitations. They are not a complete multi-provider or
  paper evaluation.
- `reports/cohort_rebuild_v4/REVEST_STRICT_PROMPT_BATCH_STATUS.json`: seven
  HTTP-200 provider responses and token/ledger receipts are retained, but zero
  cases completed because the response schema was invalid. This is a failure
  record, not localization or quality evidence.
- `reports/reproducibility/legacy_115_diagnostic/feature_fusion_validation/`
  and `fusion_regularization/`: the fixed legacy diagnostic reruns and raw
  predictions are present. They were not used for further tuning or promotion.
- `data/models/calibrator.json`, `calibrator_metrics.json`, and
  `calibrator_cv_metrics.json`: the model is finite and feature-name
  consistent, but the retained artifact lacks deployable production schema,
  disjoint provenance, fold metadata, ECE, and row-level OOF predictions.
- `reports/claim_evidence/measured_cost_run.json`, its state file, the zero-spend
  proof, and the historical runtime-cost snapshot: no completed 100-case
  provider workload exists. Retained arithmetic is modeled hybrid `$0.039` vs
  all-cloud `$0.060`, or 35%; the old 58% overall statement remains
  contradicted.

No new eligible cohort, source-bound function-ground-truth set, original
prediction bundle, independent baseline output, complete calibration provenance,
or completed provider quality/cost study was recovered. No new experiment was
therefore validly dispatched.

## Reproducibility defect investigation

The source-audit mismatch is a workspace-state discrepancy, not a supported
implementation correction:

- Clean `HEAD` `reports/claim_evidence/source_resolution_audit.csv` contains
  231 rows and 70 `UNRESOLVED` rows.
- The preserved dirty worktree version contains 231 rows and 68 unresolved
  rows; its derived local summary reports 69 and is stale relative to that
  input.
- The test requires at least 70 because that is the committed audit's declared
  coverage. The current dirty artifact also contains transient HTTP-status
  changes and is unrelated pre-existing work.

The source and derived dirty artifacts were deliberately not normalized or
staged. The failing assertion was not weakened, and no source evidence was
rewritten to obtain a green suite. A clean checkout of the committed audit is
the evidence-supported state for this test; the local dirty mismatch remains an
explicit workspace blocker.

The reproducibility package was also checked for concrete path/runtime issues:
`.python-version` is `3.11.9`, `requirements.lock` is present, Docker pins
`python:3.11.9-slim-bookworm` and installs the lockfile, and `Makefile` exposes
offline `test`, `judge`, and cohort-validation commands. The README had stale
scientific wording that called the 231-row historical CSV “strict verified” and
described staged research candidates as a reproducible benchmark. That wording
was corrected to distinguish historical inputs, staged candidates, and the
14/246 root and 22/246 v4 accepted cohorts.

## Validation performed

- `python scripts/reproduce/run_all.py`: all seven retained historical checks
  passed (`0.7586`, `35.0`, `6.1`, `17`, `82`, `231`, `8`). These are offline
  reproductions of saved/descriptive artifacts, not paper-scale proof.
- Root, v3, and v4 cohort validators: all exit 0 for manifest integrity and
  report `BLOCKED-BY-DATA` with 14/246, 20/246, and 22/246 respectively.
- `python scripts/research/verify_batch_e_result.py`: PASS; Batch E remains
  R@1 `14/40`, R@3 `27/40`, R@5 `33/40`.
- Batch D retained freeze hash: `e349997c875542ffb85a2205dbc4357e31d547c7dffb3cf1f12aebf3634becf7`; its frozen one-pass address+selector scoring remains R@1 `2/10`, R@3 `3/10`, R@5 `4/10`.
- Focused runtime/claim-ledger tests: `8 passed`.
- Direct source-audit regression: `1 failed`, with exact assertion
  `summary["unresolved_rows_attempted"] == 68`, required `>= 70`.
- Full-suite attempts were made with the current workspace. A complete run did
  not finish within the 360-second bound; the latest previously completed run
  remains `1065 passed, 7 skipped, 1 failed`, with the preserved source-audit
  assertion as the only observed failure. The current collection contains 1076
  tests, including five preserved untracked candidate-generation tests; no
  additional failure was observed from those tests.
- Docker Linux execution and `pdflatex` remain unavailable in this environment;
  no Docker build/run or PDF compilation is claimed.

## Claim ledger status

The retained 31-claim ledger remains precise and unchanged in disposition:

| Status | Count |
|---|---:|
| `VERIFIED_IMPLEMENTATION` | 11 |
| `CONTRADICTED_BY_CURRENT_EVIDENCE` | 4 |
| `EXTERNALLY_BLOCKED` | 14 |
| `UNVERIFIED` | 2 |
| `REPRODUCED_EMPIRICAL` | 0 |

The full per-claim status, verdict, prerequisites, and evidence paths remain in
`reports/claim_closure/local_snapshot/claim_ledger.json` and
`reports/provenance_hunt/FINAL_REPORT.md`. No 100-point rubric was found in the
authorized repository, so no progress score is invented.

## Remaining external dependencies

Scientific closeout still requires, at minimum: the missing accepted cohort
records and independent annotations; complete structured traces and
source-bound function ground truth; original predictions/scorer/configuration
and baseline outputs; disjoint calibration provenance with OOF predictions; a
preregistered 100-case routing/cost/quality workload with observed provider
receipts; the missing Compound case-study hash; authorized WAF challenge cases;
and the authors' resolution of denominator ambiguities. Local alternatives
cannot establish these claims without fabricating membership, labels,
predictions, or outcomes.
