# Paper claim implementation ledger

Baseline: `6282729ce34bd4a17cc99e750d23ad383ff4b0c1`.
Branch: `paper-claims-verified`.

## Binding scope

- Implement and prove all locally executable mechanisms. Preserve the original tests.
- No network calls, dependency downloads, paid API calls, or paper edits in this local pass.
- Empirical outcomes must be calculated from authentic observations, never supplied constants.
- Missing external access is `PENDING-CREDENTIALS`; insufficient authentic evidence is `BLOCKED-BY-DATA`.
- The cumulative paid experiment budget is $10. Approval is required before crossing it.
- Kluster waived for local development only by the user. Before any PR or push,
  the repository AGENTS.md rules apply in full and Kluster review must be re-enabled.
- Acceptance tests and the full accumulated suite must pass before a claim commit.

## Interfaces and decisions

- Runtime verdict/feedback work owns pipeline, configuration, orchestrator, address/fund-flow classification and human interface.
- Routing work owns query-time agents, provider adapters, cost tracking and budget enforcement.
- Storage work owns raw opcode normalization, replay/cache identity, detector profiles and tier semantics.
- Evidence work owns dataset validation, claim registry, experiment runners, reports and release scripts.
- Historical 201 tests remain intact; additional tests increase the final total.
- The paper's fixed numerical claims are targets to measure, not implementation constants.
- Paper-profile behavior may be explicit in production calls while legacy low-level behavior remains available for compatibility.
- Record compiled EVM execution as pending if local compiler/EVM binaries are absent; never label hand-authored traces authentic captures.

## Progress

- Baseline committed; all original 201 tests passed before changes.
- Local mechanisms, fixture-backed external boundaries and real experiment runners are implemented.
- Every claim commit is tested against its isolated accumulated Git snapshot; snapshots are ignored build outputs.
- Original test-source hashes are frozen in `benchmark/baseline_tests.json` and checked by the reproduction runner.
- No network requests, dependency downloads, paid experimental requests, PRs or pushes were made.
- Missing compiler/EVM tools remain pending; missing authentic 246-row acquisition evidence remains blocked by data.
- The generated `reports/local_verification/claim_report.md` contains current counts, claim statuses, tests and commit provenance.
