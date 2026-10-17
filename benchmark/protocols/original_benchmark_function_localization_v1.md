# Original-benchmark function-localization protocol v1

**Status: frozen before measurement.** This protocol defines a new measurement
on the original FaultSeeker benchmark. It does not edit or retroactively verify
the implementation paper.

## Immutable input

- Source repository: `https://github.com/kairanskrr/FaultSeeker`
- Source commit: `72753bd833554449efa8499f0d1775a97fb5c696`
- Imported files: `benchmark/original_faultseeker/ground_truth/*.json` and
  `benchmark/original_faultseeker/benchmark_classification.csv`
- Expected ground-truth files: 115
- Ground-truth source: upstream function-level `location` mappings.
- Original file bytes are copied unchanged; the harness computes and records
  SHA-256 digests for all inputs.

## Evaluation rules

1. Evaluate every one of the 115 ground-truth transaction files exactly once
   per configured variant. No transaction is selected, removed, reordered, or
   replaced based on model output.
2. A target is a function-level location parsed from the upstream `location`
   mapping. Address and function identity are both required when available.
3. Predictions are ranked function candidates. Recall@k is 1 if any expected
   target is matched by a prediction in the first k positions, otherwise 0.
   The aggregate is the mean over all 115 cases, including failures as zero.
4. Missing source, RPC/trace failure, model failure, timeout, empty prediction,
   or malformed output is retained as a failure row and contributes zero to
   Recall@1/3/5. No case is silently skipped.
5. The harness records raw output and an error/status record for every case.
6. A deterministic seed is fixed at `20261017`; it is used only for stable
   ordering/tie handling and is not used to tune or select transactions.
7. The LLM-free FunctionRanker baseline runs first. Any API-backed variant
   uses the production default model configuration unless explicitly recorded
   in the run manifest. Exact model/provider/version strings are recorded.
8. Token usage is taken from provider responses when available. Missing usage
   is recorded as missing, not estimated as measured usage. List-price
   equivalent is calculated separately from actual free-tier cost.
9. API execution is permitted only for a provider/model whose free-tier status
   has been verified before dispatch. On rate-limit, quota, billing, payment,
   or plan-required response, execution stops immediately and saves state.
10. Synthetic fixtures, compiled-local executions, and historical replay
    artifacts are not mixed into this 115-case denominator.

## Outputs

Each run writes:

- a manifest with protocol, input digests, model/provider identities, and seed;
- one raw JSON result per transaction;
- an aggregate JSON/CSV with Recall@1/3/5, failure counts, token totals, and
  list-price-equivalent cost;
- a resumable state file if execution stops before all cases finish.

## Claim boundary

This protocol can support a new measurement on the original benchmark. It does
not by itself verify the implementation paper's Table II, Table IV, Table V,
246-row cohort, reentrancy F1, or routing-cost claims.
