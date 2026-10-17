# Strict paper-implementation audit — final report

Date: 2026-10-17. Branch: `demo-ready`. No push performed. Paper files were
not edited. Dotenv/provider credentials were not loaded and no API/model call
was made.

## 18-claim before/after table

| # | Before | After | Evidence-backed disposition |
|---:|---|---|---|
| 1 | VERIFIED | REWORD | Frozen 231-row CSV and source-field audit only; provenance-complete cohort not established. |
| 2 | VERIFIED | VERIFIED (local-only) | The canonical local record supports 201 original tests passed; this does not verify paper experiments. |
| 3 | VERIFIED | REWORD | Frozen snapshot is 231 rows/eight chains; Ethereum is 132/231, not the paper's 10-chain/47.6% population. |
| 4 | VERIFIED | REWORD | 82 distinct label strings exist; 36 mapped and 46 have no reviewed SWC equivalent; semantic classes are not independently established. |
| 5 | VERIFIED | REWORD | Stored class proportions are 19/62/91/59; the paper's complexity percentages are not reproduced. |
| 6 | VERIFIED | REWORD | 17 rows carry a reentrancy label; 2 have retained traces, 15 do not, and 0 incidents are independently verified. |
| 7 | VERIFIED | UNVERIFIABLE | Paper Table V SSTORE/structural/repeated detector numbers and gains lack retained per-transaction predictions and authenticated cohort evidence. |
| 8 | REWORD | UNVERIFIABLE | Paper Table IV/adversarial-retention result is not reproduced; saved proxy rows are not the claimed N=250 study. |
| 9 | VERIFIED | REWORD | Hash/source fields exist; incident authenticity, annotation correctness, and source independence are not established. |
| 10 | REWORD | REWORD | Provider/chain support is counted only after a required historical trace response; the free probe produced none. |
| 11 | REWORD | REWORD | Measured run did not start: N=100 completed 0 because the tracked preregistered 100-ID/50-30-20 selection manifest is absent; extension not started. 35.0% remains modeled only. |
| 12 | REWORD | REWORD | Future-work/limitation text is not an empirical result; paired usage, quality, provider, and confidence evidence remain missing. |
| 13 | VERIFIED | REWORD | Retained summary records 7/115 top-1 hits (6.1%); raw prediction replay and clean denominator are unavailable. |
| 14 | REWORD | REWORD | Eight-chain endpoint observations exist, but no usable historical trace response was obtained. |
| 15 | DROP | DROP | Compound/cToken case study lacks exact transaction, trace, and source linkage. |
| 16 | DROP | DROP | Table VI confidence averages lack production PMS/CES/TCS/LCS vectors. |
| 17 | DROP | DROP | No accepted paired 20-case guidance study, selection policy, or quality aggregation exists. |
| 18 | REWORD | VERIFIED (workflow-only) | Offline reproduction commands run without provider/model calls; this does not verify paper-scale claims. |

The detailed sentence ledger is `CLAIMS_FINAL.md`; the required paper-change
ledger is `PAPER_FIXES.md`.

## What was built

- Evidence-separated evaluation report:
  `reports/claim_evidence/evidence_upgrade.json`.
- Offline runner:
  `scripts/run_evidence_upgrade.py`.
- Synthetic and compiled-local mechanism cases are explicitly excluded from
  empirical denominators.
- Historical replay accounting validates artifact digest, gzip JSON, receipt
  match, storage normalization, storage ownership, and duplicate identity.
- Opt-in provenance and evaluation partitions:
  `faultseeker/research/evidence_provenance.py`,
  `faultseeker/research/trace_capability.py`,
  `faultseeker/research/evaluation_partition.py`, and
  `faultseeker/research/routing_audit.py`.
- Machine-readable feature matrix and path-level scope notes:
  `docs/research/IMPLEMENTATION_FEATURE_MATRIX.md` and
  `faultseeker/research/paper_mechanisms.py`.
- Zero-spend proof:
  `reports/claim_evidence/cost_zero_spend_proof.json`.
- Reentrancy trace audit for all 17 labeled rows:
  `reports/claim_evidence/reentrancy_replay_verification.csv`.
- Network-free local alternate-source audit for all 70 unresolved rows:
  `reports/claim_evidence/source_resolution_local_audit.csv` and
  `source_resolution_local_summary.json`.

## Measured and blocked values

| Item | Result | Scope/blocker |
|---|---:|---|
| Synthetic hand-authored cases | 4 | Mechanism-only; not empirical. |
| Compiled EVM cases | 3 | Authentic local execution artifact; not population data. |
| Valid retained historical captures | 2 | Both Ethereum; no independent incident adjudication. |
| Metric-eligible real captures | 0 | Claim gate remains blocked. |
| Reentrancy-labeled rows | 17 | Label-string count only. |
| Trace-present labeled rows | 2 | Trace presence does not verify incident labels. |
| Trace-absent labeled rows | 15 | No qualifying local call-trace artifact. |
| Independently verified reentrant incidents | 0 | No incident label was promoted. |
| Local alternate-source resolutions | 0/70 committed rows | DeFiHackLabs/rekt absent; one DeFiLlama file scanned; zero network requests. A later dirty HTTP audit snapshot classified 73 rows as unresolved; it was preserved and not staged. |
| Local model/API workload | Not run | No local model executable; free-tier availability intentionally unverified. |
| Cost saving | 35.0% modeled | $0.039 hybrid vs $0.060 cloud-only under retained assumptions. |
| Measured cost run | N=100: 0 completed; extension: not started | Blocked before dotenv/provider loading because no tracked preregistered selection manifest binds 100 unique IDs to 50/30/20 tiers. |

## Reproducibility checks

The current branch was checked with the offline environment and no provider
credentials:

```text
focused evidence tests: 11 measured-cost tests passed
full pytest:             989 passed, 7 skipped
offline judge:           exit 0; Stage 1 only; Stage 2 skipped; llm_cost=0.0
five-line reproduction:  7/7 PASS
evidence upgrade:        4 synthetic + 3 compiled; 2 valid real; 0 eligible
```

The clean archive rehearsal used the pinned lockfile and the new Dockerfile.
The isolated offline install was blocked because
`aiohappyeyeballs==2.6.1` was unavailable from the local package cache. The
host has no `make` command, so equivalent direct commands were used; Docker is
installed but was not built because dependency installation would require
network access. These are environment/build gaps, not evidence for any paper
claim.

## Commits in this work

```text
4f2e732 docs: tighten paper claim audit
56d5107 feat: add opt-in paper mechanism audit surfaces
68e026f docs: complete paper mechanism coverage matrix
726b50f audit zero-spend replay and local sources
6155a79 fix: keep evidence report line endings portable
75afeed feat: add evidence-separated evaluation lane
9ef9078 docs: add final strict audit report
c8575a7 chore: pin reproducible test and container entrypoints
```

Existing unrelated modified trace/forensics artifacts remain untouched in the
working tree. No remote push was performed.
