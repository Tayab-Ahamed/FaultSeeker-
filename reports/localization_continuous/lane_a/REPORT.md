# Lane A outcome

Frozen grouped OOF evaluation, original110 only. Baseline R@1/3/5: 55/68/76; address coverage84/110.

| Variant | R@1/3/5 hits | Coverage | Unique109 delta hits |
|---|---|---|---|
| call_append | 55/70/78 | 86 | 0/+2/+2 |
| reference_append | 55/70/79 | 87 | 0/+2/+3 |
| train_fold_grid | 55/69/79 | 87 | 0/+1/+3 |

The label-free reference append improves two recall cutoffs without top1 regression, and increases candidate coverage by3. It does not reach61 top1. Total candidates grow677 to902. References are not verified deployed contracts: event arguments may identify recipients or callers. Conservative call-only append still gains2 coverage and2 hits at R3/R5. Neither result is a confirmatory generalization estimate after this research process; all results are exploratory.

Input features use only the pinned manifest prediction whitelist and cast.output_tail. Trace tails are at most1200 characters, so missing ancestors limit proxy/depth inference and absent calls are not negative evidence. No GT-linked source, RPC, other batch, or external lookup was used. Raw manifest row schema was inspected once and found identical to manifest schema; no raw contents enter features. No full trace data was available in this input.

Four tests pass: poisoned unknown labels ignored; call/proxy/event handling; warnings/long hashes/zero addresses excluded; held-out labels cannot affect fit configuration. Candidate identity is for joining/evaluation only; FEATURES lists only numeric fields. The inherited fixed group splitter uses labels solely for leakage grouping, as specified by the base protocol. Reusable extraction API was provided to lane C for learned models.
