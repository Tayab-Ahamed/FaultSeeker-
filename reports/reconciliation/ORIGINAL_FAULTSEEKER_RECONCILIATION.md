# Original FaultSeeker / FaultSeeker++ reconciliation

Date: 2026-10-19
Current project HEAD: `fd502a668bd480ad1bac6daa71267e90b0be8c80`
Upstream source: <https://github.com/kairanskrr/FaultSeeker>
Upstream commit and `main` tree used: `72753bd833554449efa8499f0d1775a97fb5c696`

The upstream repository was shallow-cloned and inspected at the commit above.
The local imported files identify the same commit in
`benchmark/original_faultseeker/ATTRIBUTION.md`. The upstream paper PDF was
also retrieved from that commit: 13 pages, SHA-256
`9c2213ecd01987edd079c22ac90d9fc2c3dc3845b8afbd0b62fc6a176752e3ba`.

## Source artifacts inspected

From the upstream repository:

- `README.md` and `benchmark/README.md`.
- `benchmark/benchmark_classification.csv`.
- `benchmark/ground_truth/*.json`.
- `faultseeker/core/pipeline.py`.
- `faultseeker/forensics/{orchestrator,trace_analyzer,fund_flow_analyzer,address_classifier,result}.py`.
- `faultseeker/data_collection/{trace_parser,txn_replayer,txn_info_collector,txn_sequencer,contract_downloader}.py`.
- `faultseeker/function_analysis/{function_ranker,function_analyzer}.py`.
- `requirements.txt`, `setup.py`, and `foundry.toml`.
- `full_paper/FaultSeeker LLM-Empowered Framework for Blockchain Transaction.pdf`.

The upstream README describes a two-stage pipeline: transaction forensics,
then function analysis. The upstream `FunctionRanker` is a deterministic
count-based ranker with filtered safe functions and a fallback to observed
function-call locations; it is not the paper's complete GPT-4o multi-agent
experiment by itself. Upstream dependencies use lower bounds (`>=`) and the
upstream repository does not provide the current project's pinned lockfile or
reproducible benchmark runner.

## Denominators and row identity

All overlap calculations use `chain:lowercase_transaction_hash`. The complete
row-level artifact is:

- `reports/reconciliation/row_level_overlap.csv`
- `reports/reconciliation/original_benchmark_reconciliation.json`

The artifact preserves ground-truth function identities as
`address#function`, rather than treating a vulnerability label as a location.

| Population | What it actually contains | Count |
|---|---|---:|
| Root classification | Parsed rows in `benchmark/benchmark_classification.csv` | 115 |
| Imported upstream classification | Parsed rows in `benchmark/original_faultseeker/benchmark_classification.csv` | 115 |
| Imported upstream ground-truth files | Upstream `location` JSON files | 115 files |
| Unique upstream ground-truth transaction IDs | Stable IDs after filename/transaction reconciliation | 114 |
| Upstream ground-truth files with function identities | Every imported file has at least one function identity | 115 files |
| Current localization denominator | Unique stable IDs used by the current selector-normalization report | 114 |
| Current FaultSeeker++ accepted root cohort | Accepted records in `benchmark/cohort_manifest.json` | 14 |
| Current FaultSeeker++ target specification | Root manifest target, not an accepted dataset | 246 |
| Current FaultSeeker++ unresolved target remainder | `246 - 14` | 232 |
| Versioned v4 accepted cohort | Accepted records in `benchmark/versions/cohort_v4_20261016/cohort_manifest.json` | 22 |
| Versioned v4 target specification | v4 manifest target, not an accepted dataset | 246 |
| Versioned v4 unresolved target remainder | `246 - 22` | 224 |

The two classification CSVs contain the same 115 parsed rows and the same
stable-ID set. They are not byte-identical: the imported copy uses CRLF line
endings while the root copy uses LF line endings. The current accepted
FaultSeeker++ cohort overlaps the original benchmark on exactly four stable
IDs:

- `eth:0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb`
- `eth:0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c`
- `eth:0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa`
- `eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d`

One important identity defect is retained rather than silently fixed:
`0x6439d63c...` and `0x72a25227...` are two ground-truth filenames whose
`transaction_hash` fields both contain `0x6439d63c...`. They have different
location mappings. This explains why a 115-file source population becomes a
114-identifier localization population. The overlap CSV records both source
filenames under that stable ID.

The 246 value therefore cannot be read as “246 attacks evaluated.” It is the
target size of the cohort specifications. The root manifest currently accepts
14 records and leaves 232 unresolved; the versioned v4 manifest accepts 22
unique stable IDs and leaves 224 unresolved. Both manifests explicitly state
that independent human review has not occurred. The v4 manifest is included as
a separate versioned comparison and is not merged into the root overlap CSV.

## Original paper evaluation claims

The paper's evaluation section (pages 7–10 of the retrieved PDF) states:

| Paper item | Paper denominator/settings | Reported result | Supporting artifact status |
|---|---|---|---|
| Dataset | 115 malicious transactions; 84 DAppFL + 381 DeFiHackLabs, 9 overlaps removed; Ethereum/BNB and expert annotations; complexity 14 moderate / 51 complex / 50 extreme | 115 total; 879 total function calls and dataset-wide averages for other columns | The 115 CSV/ground-truth corpus and complexity labels are present. The claimed selection history, three-expert consensus, and source-availability metadata are not present as raw adjudication artifacts. |
| Table II, FaultSeeker vs DAppFL | All 115; Recall@1/3/5; complexity strata 14/51/50 | FaultSeeker `50.43% / 73.91% / 76.52%`; DAppFL `6.09% / 12.17% / 14.78%` | No upstream raw prediction files, DAppFL outputs, scorer, or run log supporting these exact values were found. Current provider-pinned results are a new measurement, not a reproduction of Table II. |
| RQ2 native LLM comparison | Stratified 30 rows, 10 per complexity; GPT-4o, Claude 3.7 Sonnet, DeepSeek R1; top-5 success | Figure 6 qualitative/count comparison; exact per-row outputs are not in the repository | Missing raw prompts, model versions, responses, and per-example success rows. |
| Table III ablation | Same paper dataset; complete and four variants | Complete `10/42/41 = 93`; no-forensics `0/2/0 = 2`; no-organizer `7/20/11 = 38`; no-coordinator `2/23/7 = 32`; no-specialized-workers `1/15/5 = 21` | No raw ablation outputs, exact execution configuration, or independent per-example scorer found. Also, the table's “successful localizations” denominator is not reconciled to the Table II top-k counts. |
| Table IV efficiency/cost | Complexity levels; Stage 1/Stage 2/total seconds; GPT-4o price equation with `$40/$80` per million tokens | Moderate `2.72 + 262.77 = 265.49s`, `$1.55`; complex `7.87 + 446.53 = 454.40s`, `$3.04`; extreme `33.58 + 484.40 = 517.98s`, `$4.53` | No raw token ledger, provider receipts, latency samples, or pricing snapshot found. Current project cost evidence explicitly remains modeled or blocked. |
| Source-unavailable claim | 52 cases without source code | FaultSeeker allegedly localizes all 52 while DAppFL cannot operate | The classification/ground-truth files do not carry a reproducible source-availability flag and no 52-row audit was found. |
| RQ5 Orion case study | One qualitative transaction analysis with GPT-4o | Identifies `depositAsset()` through intermediate task-tree evidence | The paper narrative is present; no raw GPT-4o transcript or immutable case-study run artifact is present. |
| Abstract efficiency claim | Real-world practical efficiency | `4.4–8.6` minutes and `$1.55–$4.53` per transaction | Only the paper table supports the number; raw measurement artifacts are missing. |

The original paper says its annotations were validated by security experts and
that two experts independently developed the suspicious-pattern checklist.
The upstream ground-truth JSON files contain locations, incident metadata, and
disclosure links, but no reviewer identities, agreement record, or annotation
adjudication log. Those claims are consequently not independently replayable
from the repository alone.

## Original evaluation execution

The current project has two distinct executable paths and they must not be
confused:

1. `python benchmark/original_benchmark_eval.py` is a new LLM-free evaluation
   harness. Its retained full run used the 115 upstream ground-truth files but
   attempted live current-code orchestration. It completed 2 rows, failed 101
   with `RuntimeError` (“orchestrator returned no result”), and timed out on 12.
   Its all-115 Recall@1/3/5 was `0/0/0`. The first concrete missing dependency
   is a complete compatible transaction-trace/RPC execution path for the
   upstream 115 cases; the upstream location JSONs are not execution traces.

2. The retained provider-pinned run at
   `reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/`
   is a completed **new measurement** on the original benchmark. It has 115
   per-case rows, 110 successful rows, 5 trace failures, and 14 replay mismatch
   flags. Its all-115 metrics are Recall@1/3/5 =
   `25/115 = 0.217391`, `49/115 = 0.426087`, and `52/115 = 0.452174`.
   The valid-trace-only subset is `25/110 = 0.227273`,
   `49/110 = 0.445455`, and `52/110 = 0.472727`.

The current project independently re-aggregated the retained per-example rows
and wrote:

- `reports/reconciliation/original_evaluation_recomputed.json`

The recomputation exactly matches the retained provider manifest aggregates.
This validates aggregation bookkeeping only. It does **not** reproduce the
upstream paper's Table II: the provider-pinned run uses the current harness,
current code, and a scorer whose selector lookup registers ground-truth
function names. That scorer boundary is recorded in the recomputation artifact
instead of being presented as an unbiased upstream reproduction.

## Recovered trace evidence

The bounded dRPC run at
`reports/external_runs/phase2/20261017T011500Z/drpc/` was audited without making
new requests or rerunning ranking. It contains 9 captured rows and 6 failed
attempts. Four captured rows are also in the imported original ground-truth
corpus; all four show the labeled target address in the raw callTracer tree.
Public typed-signature evidence maps the imported labels to observed selectors
for all four rows: `cacheAssetPrice()`, `latestAnswer()`,
`doSwapThroughOrionPool(...)`, and `donateToReserves(uint256,uint256)`.

This recovers execution and function-identity evidence for four individual
cases; it is not a replacement for the missing original predictions,
transcripts, scorer, or 115-row paper run. The machine-readable audit is
`reports/reconciliation/recovered_trace_audit.json` and the human-readable
report is `reports/reconciliation/RECOVERED_TRACE_AUDIT.md`.

The frozen protocol remains explicit in
`benchmark/protocols/original_benchmark_function_localization_v1.md`: failures
stay in the 115 denominator, synthetic/replay fixtures are not mixed into that
denominator, and the new measurement does not verify the paper's original
Table II, Table IV, Table V, 246-row cohort, or cost claims.

## Next executable FaultSeeker++ experiment

Feature fusion was not extended. The next highest-value executable result is
the existing leakage-safe grouped candidate-generation cross-validation on
the retained provider-pinned population:

- Script: `scripts/research/evaluate_candidate_generation_cv.py`
- Result: `reports/research_results/candidate_generation_cv_reviewed_20261018.json`
- Population: 110 successful saved rows only; no Batch B/C directories read.
- Five grouped folds, 98 connected groups, 324 training-only weight
  configurations per fold, public selector cache only, ground-truth name
  registration disabled.
- Baseline: R@1 `40/110`, R@3 `55/110`, R@5 `58/110`, candidate recall@20
  `68/110`.
- OOF candidate-generation ranking: R@1 `40/110`, R@3 `56/110`, R@5
  `58/110`, candidate recall@20 `69/110`.

This is a saved-evidence exploratory experiment, not a new held-out claim or a
production-default change. It is materially more useful than further tuning
the already-saturated legacy feature-fusion calibrator because it tests a
different localization bottleneck and preserves the original cohort boundary.

## Reproducibility and integrity boundaries

- Frozen Batch E was not read or modified by the reconciliation script.
- No labels, locations, transaction IDs, or denominators were repaired or
  rescored.
- Pre-existing dirty/untracked files were preserved.
- The reconciliation script is read-only with respect to source evidence and
  writes only the new `reports/reconciliation/` artifacts.
