# Batch A adapter-fix changelog

**Label: post-diagnostic adapter fix, exploratory.**

The adapter patch was prepared to reuse the original benchmark's deterministic Stage-1 path:

1. Replace the old empty-candidate fallback with the original `ForensicsOrchestrator` flow.
2. Reuse `AddressClassifier.run` for address filtering and candidate selection.
3. Reuse the original orchestration hooks: flashloan fallback, hashed-function expansion, created-contract expansion, other-function fallback, and `AdaptiveFailureAwareController.apply`.
4. Construct the production `ForensicsResult` before invoking the unchanged `FunctionRanker`.
5. Keep the existing `TransactionSequencer` canonical callTracer conversion; its mapping already matches the production `_canonical_to_legacy_trace` fields.
6. Keep address normalization and selector/name matching in the existing localization helpers; no new checksum or selector implementation was added.

The one permitted control run stopped before the hard gate due to an adapter bridge state-name typo (`tx_hash` versus `txn_hash`). The typo was corrected after the stop. Controls and Batch A were not rerun.
