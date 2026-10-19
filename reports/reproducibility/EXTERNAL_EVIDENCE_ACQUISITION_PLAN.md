# FaultSeeker++ external evidence acquisition plan

This plan is part of the claim-closure checkpoint. It describes the minimum
new evidence required to reopen blocked claims. It does not authorize network
requests, provider calls, paid spend, transaction submission, or changes to
frozen batches.

## General admission rules

Every new evidence package must include:

1. A preregistered selection manifest with chain-qualified transaction identity.
2. Immutable input and output SHA-256 digests, code revision, runtime version,
   exact command, and exit code.
3. Transaction, receipt, trace, and block identity checks where applicable.
4. Source artifacts retained locally, with publisher identity and independence
   rationale.
5. Annotation records with reviewer identity/qualification or explicitly
   authorized public-source consensus; no inferred labels.
6. A sealed development/held-out split before model fitting or threshold choice.
7. Integer denominators, exclusions, missingness, and uncertainty calculations.
8. No reuse, retuning, or overwrite of frozen Batch E or any sealed held-out
   artifact.

## Blocked empirical claims

| Claims | Minimum provider/input | Required artifact | Independent validation / acceptance |
|---|---|---|---|
| 3, 4, 5, 6, 7, 8 — cohort size, sources, chains, taxonomy, complexity and reentrancy | At least 246 unique chain-qualified incidents, including the missing 10-chain coverage, canonical receipts/traces, two independent security publishers per incident, and qualified adjudication | Versioned manifest, bound transaction/receipt/trace/source/annotation artifacts, admission decisions, frozen split, and cohort summary | `benchmark.validate_cohort_manifest` accepts every row; target count is 246; no duplicate identity; source and reviewer independence checks pass; all published proportions are recomputed from accepted rows |
| 13, 14 — detector precision/recall/F1 and claimed gains | Frozen accepted cohort with complete comparable trace features for positives and negatives, plus preregistered baseline implementations | Per-transaction predictions for every system, confusion matrices, denominators, paired outcomes, bootstrap/uncertainty output | Same eligible rows and labels for every system; no leakage; exact integer TP/FP/TN/FN; metrics regenerate from raw predictions; no held-out tuning |
| 15 — Compound case study | Exact legitimate Compound/cToken transaction, trace, source linkage, and function ground truth | Bound case-study transaction/receipt/trace/source/ground-truth package and executed localization output | Hash/receipt identity matches; source identifies the same case; function target is independently supported; output is reproducible from the recorded command |
| 17 — six provider families | Authorized credentials or documented public test endpoints, plus an available local Ollama model where required | Per-provider conformance manifest, request/response schema captures, model identity and usage receipts | All six adapters pass native schema and usage checks; secrets are not committed; unavailable providers remain blocked |
| 18 — 58% cost savings and 100 paired runs | Preregistered 100-transaction selection with exact 50/30/20 workload, authorized provider execution, dated pricing, observed token usage, and paired quality/rank outcomes | Selection manifest, per-call usage ledger, pricing snapshot, paired baseline/hybrid outputs, quality/rank report, resumable state | Exactly 100 eligible transactions; observed usage exists for every call; measured cost and counterfactual recompute; quality/rank bounds pass; 58% is not substituted for the 35% modeled result |
| 21 — 40% benign prefilter and latency reduction | Independently verified benign workload and paired full/prefilter executions | Selection manifest, benign adjudication, per-transaction stage decisions and latency logs | Benign denominator is independently valid; prefilter rate and latency recompute from raw rows; no missing rows are counted as benign |
| 22 — multi-agent localization | Provider authorization, verified contract source, exact function-level ground truth, and an immutable new holdout | Per-role prompts/responses, source digests, ranked functions, target functions, and localization metrics | Function-level targets match source evidence; Recall@1/3/5 and denominators regenerate; no Batch E reuse or target leakage |
| 25 — multi-chain RPC capability | Authorized archive/trace-capable endpoints for requested chains and sustained recovery probes | Request/response captures, capability matrix, endpoint identity, and failure/recovery ledger | Required historical trace methods succeed according to the declared protocol; unsupported chains remain explicitly unknown |
| 27 — 23% WAF bypass | Authorized challenged-request corpus with a real denominator, versioned challenge strategy, and attempt logs | Challenge cases, every recovery attempt, outcomes, denominator, and strategy version | Percentage recomputes from authorized cases; RPC success is not used as a WAF result |
| 28 — Table VI category averages | Accepted production rows with observed PMS/CES/TCS/LCS vectors and declared category mapping | Per-function component vectors, categories, missingness ledger, and aggregation script | Every average recomputes from observed vectors; receipt gas/call proxies are not substituted |
| 29 — 20-case guidance improvement | Original or newly preregistered 20-case selection, guidance policy, paired rankings, and explicit aggregation | Input manifest, before/after rankings, guidance actions, integer outcomes, and aggregation code | Paired outcomes and denominator are complete; 68→81% is reported only if the declared aggregation supports it |

## Locally actionable but not yet closed

| Claim | Local action | Acceptance |
|---|---|---|
| 2 — original test claim | Run the full current suite after the pre-existing source-audit artifact mismatch is resolved or isolated in a clean revision | Current revision reports exact pass/skip/fail counts and original baseline digests remain unchanged |
| 30 — reproduction scripts | Keep the offline runners and claim ledger deterministic; run the scoped reproduction commands without treating them as paper-scale reproduction | Every command reports inputs, digests, denominators, and explicit blocked status where evidence is absent |
| 23 — Equation 4 confidence | Preserve heuristic-versus-probability separation and the calibration audit | Heuristic implementation tests pass; legacy/provenance-invalid calibrators remain rejected |

## Current source-audit blocker

`tests/test_t3_evidence_audits.py` expects at least 70 unresolved source rows.
The current dirty `reports/claim_evidence/source_resolution_audit.csv` contains
69 rows with `source_status=UNRESOLVED`, while the dirty
`source_resolution_local_summary.json` claims 72. The implementation correctly
counts the input CSV rather than trusting the stale summary. This is an
artifact-consistency problem, not evidence that any source was resolved.

The safe resolution is to reconcile the dirty evidence artifacts from their
provenance-producing run or restore a clean, hash-bound snapshot. No row should
be added merely to satisfy the test, and no successful resolution or
adjudication should be inferred.

## Completion conditions

Scientific completion requires all mandatory empirical claims either to have
the artifacts and checks above or to be explicitly reworded/dropped. Local
implementation checks, modeled cost arithmetic, simulated controls, and
historical summaries cannot substitute for the listed evidence.
