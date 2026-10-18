# Phase 1 address-ranking OOF results

**Exploratory development only. Original110 records,109 unique transaction hashes;98 connected groups; five outer folds of22 rows.**

## Main results — Wilson 95% intervals

| Variant | R@1 | R@3 | R@5 |
|---|---|---|---|
| Current distinct-address baseline | 55/110 (50.00%; [40.82, 59.18]) | 68/110 (61.82%; [52.49, 70.35]) | 76/110 (69.09%; [59.93, 76.96]) |
| reciprocal_sum | 55/110 (50.00%; [40.82, 59.18]) | 69/110 (62.73%; [53.41, 71.19]) | 77/110 (70.00%; [60.88, 77.77]) |
| structural_grid | 54/110 (49.09%; [39.94, 58.30]) | 67/110 (60.91%; [51.57, 69.51]) | 76/110 (69.09%; [59.93, 76.96]) |
| delegate_context_grid | 54/110 (49.09%; [39.94, 58.30]) | 67/110 (60.91%; [51.57, 69.51]) | 76/110 (69.09%; [59.93, 76.96]) |

Selection: **reciprocal_sum only**, provisionally for later approval. Change versus the equal-budget baseline: **0 / +1 / +1 hits** at1/3/5 (+0 / +0.91 / +0.91 percentage points). The other two variants regress at1/3 and are rejected. No production behavior is changed and no fresh evaluation is authorized or performed. This is a small observed development gain; no statistical superiority or paper-level claim is made.

## Equal-budget baseline and variants

Every result above ranks **distinct candidate addresses**. The baseline takes current production `rerank_saved_predictions` and keeps each address's first occurrence. All three variants use exactly the same observed-address pool. Removing duplicate function entries cannot itself count as an improvement over this baseline. Candidate coverage is84/110:26 records have no labeled target address anywhere in the common pool, imposing an empirical ceiling of76.36% for these ranking-only variants. No address or source target is invented.

### Current production function-slot reference — different budget

| Variant | R@1 | R@3 | R@5 |
|---|---|---|---|
| Address hits in undeduplicated current function list | 55/110 (50.00%; [40.82, 59.18]) | 68/110 (61.82%; [52.49, 70.35]) | 71/110 (64.55%; [55.25, 72.86]) |

This55/68/71 reference measures addresses within the first1/3/5 **functions**, while55/68/76 measures the first1/3/5 **distinct addresses**. The five-hit top-five compression gain is excluded from variant improvement. The previously recorded original saved ordering is also a different baseline; no historical result is relabeled as current production.

| Variant | Mechanism | Training configurations per fold | Leakage check |
|---|---|---:|---|
| reciprocal_sum | Sum reciprocal production function ranks per address; stable baseline-order ties | 1 | No fitting, labels, source URLs, incident names or address identity values in numeric scores; row-local evidence only |
| structural_grid | Mix best/summed reciprocal rank with address call count, depth, concentration and fanout | 27 | Only outer-training labels select weights; normalization uses only the individual row, with no global scaler |
| delegate_context_grid | Structural grid plus observed proxy/implementation-neighbor evidence sharing | 81 | Only explicit cached delegatecalls; both endpoints must already be candidates; no alias correctness credit; weights selected on outer training only |

Only2/110 records contain usable delegate-neighbor evidence in the saved cast tail. The selected delta is0 in all five proxy-variant folds; this run provides no incremental proxy-resolution benefit. Truncated saved trace tails limit this signal, and absence of a cached edge is not proof the on-chain transaction had no proxy.

## 109-unique reweighting of the same OOF predictions

| Variant | R@1 | R@3 | R@5 |
|---|---|---|---|
| Baseline | 54/109 (49.54%; [40.33, 58.78]) | 67/109 (61.47%; [52.09, 70.07]) | 75/109 (68.81%; [59.60, 76.74]) |
| reciprocal_sum | 54/109 (49.54%; [40.33, 58.78]) | 68/109 (62.39%; [53.02, 70.91]) | 76/109 (69.72%; [60.55, 77.56]) |
| structural_grid | 53/109 (48.62%; [39.45, 57.89]) | 66/109 (60.55%; [51.17, 69.22]) | 75/109 (68.81%; [59.60, 76.74]) |
| delegate_context_grid | 53/109 (48.62%; [39.45, 57.89]) | 66/109 (60.55%; [51.17, 69.22]) | 75/109 (68.81%; [59.60, 76.74]) |

This removes the duplicate SorStaking record's extra weight from the already-produced OOF predictions. It is **not a deduplicated refit**. Reciprocal aggregation retains0/+1/+1 hits. Both copies of the duplicate were kept in the same outer fold. The predeclared eligibility rule requires no regression at any of1/3/5 plus at least one gain, both on110 records and this unique sensitivity; only one variant meets it.

## Paired changes for the selected variant

| Cutoff | Newly hit records | Newly missed records | Net |
|---|---:|---:|---:|
| R@1 | 0 | 0 | 0 |
| R@3 | 4 | 3 | 1 |
| R@5 | 1 | 0 | 1 |

## Leakage review and fold isolation

Training selection is lexicographic training hits@1, then@3, then@5; deterministic first-config ties. Each outer validation fold is excluded from that fold's configuration search. The three mechanisms, grids and final selection rule were recorded in `PROTOCOL.md` and content-pinned in `preregistration.json` before execution. No search-space changes or second experiment were made after outcomes.

| Fold | Train | Validation | Shared hashes | Shared incident names | Shared target contracts | Shared source URLs |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 88 | 22 | 0 | 0 | 0 | 0 |
| 1 | 88 | 22 | 0 | 0 | 0 | 0 |
| 2 | 88 | 22 | 0 | 0 | 0 | 0 |
| 3 | 88 | 22 | 0 | 0 | 0 | 0 |
| 4 | 88 | 22 | 0 | 0 | 0 | 0 |

Connected components union individual classification-source URLs, normalized incident names, chain-qualified target contract addresses, and duplicate transaction identities transitively. Ground truth is read only for fold grouping and target comparisons. The ranking adapter receives only whitelisted saved candidate function/address/count/path fields and saved cast text; stored correctness/score fields are discarded. No GT selector registry or guessed ABI signature is used. An additional check of70 original GT disclosure URLs found0 cross-fold overlaps; those URLs are an extra validation check, not ranking features.

Six software tests passed: equal distinct-address pool, label/expected-field invariance, transitive shared URL/contract/duplicate grouping, observed-only delegate context, training selection invariant to changed validation labels, and a guard rejecting every `reports/new_batches/` path. Fixtures in these tests are software checks and do not enter research results. The independent evaluator review found no blocking fold-local leakage defect.

The experiment installs a runtime audit guard blocking network/subprocess operations and reads/listings under `reports/new_batches/`. No C/D files were opened, listed, hashed, scored or modified. No Batch E was created. Only the original manifest, row-bound original GT files, original classification CSV, current ranking source and this phase's files were used. Every original input and preregistered source/protocol hash matches after execution.

Limits: prior development of the upstream ranker used this original population, and three-variant selection uses OOF outcomes. Thus these results remain exploratory; fold-local isolation is not an unseen generalization guarantee. Wilson95% intervals are nominal record-level binomial intervals, not a paired gain confidence interval, and do not adjust for duplicate weighting, connected incidents, model selection or historical feature-design exposure. The small+1/+1 result needs a separately approved unseen evaluation before any generalization claim.

## Recorded outputs and command

- `results.json`: all per-row evidence, baseline and OOF ranks, per-fold train/test indices and selected configurations, metrics, eligibility decision and input/source SHA256 pins.
- `preregistration.json`: source, test and protocol hashes recorded before the experiment.
- `VALIDATION.json`: independent disclosure-overlap/hash checks and paired gains/losses.
- `PROTOCOL.md`: fixed mechanisms, grids, folds, comparator and selection rule.
- `scripts/research/address_ranking_phase1.py`: offline evaluator and candidate-address scoring adapters.
- `tests/test_address_ranking_phase1.py`: software-only safety and isolation tests.

Executed once from repository root:

```powershell
python scripts/research/address_ranking_phase1.py
```

The runner refuses to overwrite an existing results.json. Source and protocol hashes are in the recorded results. No production deployment fit or integration is performed in Phase1.

Branch: `address-ranking-oof-phase1`. Commits0; pushes0; RPC0; model-provider calls0; new batches0; paper edits0. **Stopped after Phase1 selection.**
