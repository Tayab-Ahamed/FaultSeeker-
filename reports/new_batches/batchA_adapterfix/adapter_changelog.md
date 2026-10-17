# Batch A adapter-fix changelog

Label: `post-diagnostic adapter fix, exploratory`.

## Differences found and addressed

1. The old adapter ran `TransactionSequencer.from_structured` and `TraceAnalyzer`, then passed an empty `functions_to_be_inspected` map directly to `FunctionRanker`. The original benchmark path runs `AddressClassifier.run` first and uses its normalized address filtering and candidate map.
2. The old adapter omitted the original orchestration hooks: `check_flashloan_fallback_execution`, `check_function_name_with_hash`, `check_call_with_created_contract`, `get_other_functions_to_be_inspected`, and `AdaptiveFailureAwareController.apply`.
3. The old adapter did not construct the production `ForensicsResult` with address-classifier fields, fund-flow fields, candidate fields, and adaptive-fallback metadata.
4. The patched adapter reuses `ForensicsOrchestrator`, `AddressClassifier`, `AdaptiveFailureAwareController`, `ForensicsResult`, `TraceAnalyzer`, `TransactionSequencer`, and the existing localization selector/name normalization rather than duplicating candidate-building logic.
5. CallTracer conversion was already field-equivalent to `TransactionSequencer._canonical_to_legacy_trace`: `from`, `to`, `input[:10]`, `input[10:]`, `type`, `value`, `gas`, `gasUsed`, and recursive calls. No change was required there.
6. Address normalization remains the original lowercase normalization. EIP-55 checksum casing is not used by the original rank scorer; no checksum behavior was added to scoring.

## Gate policy

The four original controls are a hard gate. Batch A is not measured unless every saved rank reproduces exactly.
