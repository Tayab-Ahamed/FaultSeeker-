# Batch A frozen-ranker measurement

**Label: new measurement, exploratory**

This one-shot offline measurement uses the frozen valid trace set and frozen Batch A source labels. It was not used for tuning.

## Frozen inputs

- Valid set: `reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json`
- Valid-set SHA-256: `fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785`
- Frozen Batch A: `reports/new_batches/batchA_candidates.json`
- Frozen Batch canonical SHA-256: `4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21`
- Ranker: `faultseeker/function_analysis/function_ranker.py`
- Ranker SHA-256: `acf6e1874aad2817ce9576a109a5acd922f2d7cb1d2b8c6e283672d926bd32f2`
- Network/RPC/credentials: none
- Prior ranker outputs: not read
- Ranker invocations: 23 (exactly once per valid trace)

## Metrics — new measurement, exploratory

| Metric | R@1 | R@3 | R@5 | N |
| --- | ---: | ---: | ---: | ---: |
| Primary address+function | 0/23 (0.0000) | 0/23 (0.0000) | 0/23 (0.0000) | 23 |
| Function-only sensitivity | 0/23 (0.0000) | 0/23 (0.0000) | 0/23 (0.0000) | 23 |

Address matching is case-insensitive. Function matching uses the existing localization semantics: normalized function names and the existing selector resolution table; no network lookup was performed.

## Counts per chain — new measurement, exploratory

| Chain | Scored rows |
| --- | ---: |
| eth | 23 |

## Skipped/blocked cases

- None. All 23 valid traces had a matching frozen Batch A label.
