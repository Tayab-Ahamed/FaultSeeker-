# Independent upstream validation closeout

## Scope

This closeout was performed on HEAD `bb0680e` after the evidence-recovery
closeout. The upstream source inspected was `kairanskrr/FaultSeeker` at commit
`72753bd833554449efa8499f0d1775a97fb5c696`. The upstream README, benchmark
classification, 115 ground-truth files, ranker implementation, paper-level
localization definition, retained evaluation scripts, and provider-pinned raw
outputs were inspected.

The upstream README defines a ranked-function task over 115 real-world attacks.
The pinned ranker filters common safe functions, keys candidates by function and
address, deduplicates repeated calls by depth, and sorts by count. No standalone
upstream scorer, original per-example prediction bundle, original model
transcripts, complete trace/source bundle, or baseline/ablation output was
available. The original paper's reported localization values are therefore
reconstructable only as a comparison target, not as an exact rerun.

## Independent calculation performed

Command:

```text
python scripts/reproduce/independent_upstream_validation.py
```

Inputs are SHA-256 bound in
`reports/reproducibility/upstream_validation/input_manifest.json`. Per-example
outputs are retained in
`reports/reproducibility/upstream_validation/localization_per_example.jsonl`.
The machine-readable 31-claim comparison is
`reports/reproducibility/upstream_validation/claim_comparison.json`, with the
readable version in `CLAIM_COMPARISON.md`.

The upstream paper reports Table II localization values of 50.43%, 73.91%, and
76.52% at Top-1/3/5 over 115 transactions, implying 58/115, 85/115, and 88/115
hits. The retained independent function-only calculation gives:

| View | Denominator | R@1 | R@3 | R@5 |
|---|---:|---:|---:|---:|
| Function-only reconstruction, all rows | 115 | 27/115 (23.48%) | 49/115 (42.61%) | 53/115 (46.09%) |
| Current address-aware scorer, all rows | 115 | 25/115 (21.74%) | 49/115 (42.61%) | 52/115 (45.22%) |
| Function-only reconstruction, valid traces | 110 | 27/110 (24.55%) | 49/110 (44.55%) | 53/110 (48.18%) |
| Current address-aware scorer, valid traces | 110 | 25/110 (22.73%) | 49/110 (44.55%) | 52/110 (47.27%) |

There were 110 retained `status=ok` outputs and five explicit failures. Failed
rows remain in the 115-row denominator and are not converted into predictions.
This is an independent LLM-free ranker calculation, not an exact reproduction
of the paper's multi-agent result.

The calculation has edge-case tests for denominator preservation, duplicate
identities, missing ground-truth labels, stable tie order, and complete 115-row
coverage. Six focused tests pass.

## Claim comparison

The generated comparison contains exactly 31 claims and preserves the existing
ledger statuses:

- `VERIFIED_IMPLEMENTATION`: 11
- `CONTRADICTED_BY_CURRENT_EVIDENCE`: 4
- `EXTERNALLY_BLOCKED`: 14
- `UNVERIFIED`: 2
- `REPRODUCED_EMPIRICAL`: 0

No status was upgraded merely because a report or implementation test exists.
The independent localization calculation is attached to claim 22 as bounded
diagnostic evidence; it does not establish the multi-agent localization claim.

## Validation and integrity

- `python -m pytest tests/test_independent_upstream_validation.py -q -p no:cacheprovider`: **6 passed**.
- `python -m pytest tests/test_runtime_layout.py tests/test_claim_closure_ledger.py -q -p no:cacheprovider`: **8 passed**.
- `python scripts/research/verify_batch_e_result.py`: **PASS**; Batch E remains R@1 `14/40`, R@3 `27/40`, R@5 `33/40`.
- Batch D remains frozen at hash `e349997c875542ffb85a2205dbc4357e31d547c7dffb3cf1f12aebf3634becf7`; its one-pass address+selector result remains `2/10`, `3/10`, `4/10`.
- Full suite: **1074 passed, 7 skipped, 1 failed** in 183.45 seconds. The only failure is `tests/test_t3_evidence_audits.py::test_local_source_audit_is_network_free_and_keeps_adjudication_separate`, where the preserved dirty source audit reports 68 unresolved rows while the test requires at least 70. The clean committed audit remains at 70; unrelated dirty evidence was not changed.
- Docker Linux engine is unavailable and `pdflatex` is unavailable. No Docker build/run or PDF compilation is claimed.

## Remaining evidence dependencies

Exact paper reproduction still requires the original scorer/configuration and
predictions, complete model/provider transcripts, all accepted 246-row cohort
records with independent annotation, complete source-bound function truth, raw
baseline and ablation outputs, disjoint calibration provenance with OOF
predictions, and the preregistered measured routing/cost/guidance/WAF studies.
No valid local alternative can establish those missing empirical claims without
inventing labels, predictions, traces, or study outcomes.
