# Original-benchmark localization scoring protocol note

**Status:** documentation/evidence only. The scorer, paper, and existing claims
files were not changed.

## Canonical metrics

The primary metric for this workspace is **address + function identity**. A
prediction is a hit only when the normalized candidate code address and the
normalized function identity match one of the transaction's labeled function
locations. This is the current saved-row scoring rule.

The sensitivity metric is **function-only identity**. It compares the
normalized function name against any labeled function name for the transaction,
without requiring the candidate address to equal the labeled address. This is
an evidence-bounded reconstruction of the paper-level function-localization
definition, not a claim that the authors used a private implementation with
exactly these rules.

## Normalization and selector handling

- Addresses are trimmed and lowercased before comparison.
- Function values are trimmed, lowercased, and truncated before `(` so a
  signature suffix does not create a separate identity.
- The primary scorer reads candidate address aliases in this order:
  `address`, `code_address`, `contract`, `callee`. Saved provider-pinned rows
  use `code_address`.
- The primary scorer reads function aliases in this order:
  `function_name`, `name`, `function`.
- In the primary scorer, a four-byte selector may be resolved to a human name
  through the local selector cache. The function-only sensitivity reconstruction
  keeps a raw selector as a raw selector and does not assume selector-name
  resolution.
- Multiple labeled locations per transaction are treated as a union: any
  matching labeled function is sufficient.
- Recall@k examines the first k ranked candidates. On the saved rows, the list
  order agrees with the stored ascending `rank` fields.
- Source-line labels are retained as line targets by the parser but do not
  count for the default function-localization metric.

## Provenance boundary

The authors did not publish a standalone scorer or an evaluator implementation
that specifies the exact equality comparator used for the paper's headline
Recall@1/3/5 values. The public imported material available here consists of
the 115 label JSON files and the authors' ranking/runtime source. The authors'
per-transaction traces, ranked predictions, and evaluation scripts were not
released in the imported repository snapshot.

The label inventory contains **115 JSON files and 114 unique transaction
hashes**: one transaction identity is duplicated across the label files. That
fact is recorded here as an input/provenance limitation and is not repaired by
the scoring audit.

## References

- Current scorer: `benchmark/honest_eval/localization.py:153-254`.
- Imported labels: `benchmark/original_faultseeker/ground_truth/*.json`.
- Frozen measurement protocol: `benchmark/protocols/original_benchmark_function_localization_v1.md:18-31`.
- Authors' repository snapshot: `third_party/original_faultseeker/README.md:7,138-147`.
- Authors' ranking representation: pinned upstream
  `faultseeker/function_analysis/function_ranker.py`, where the ranker builds
  `function_address` keys and lowercases function/address values for lookup.
- Full strictness comparison and saved-row flips:
  `reports/original_benchmark/scorer_strictness_audit_20261017.md`.
