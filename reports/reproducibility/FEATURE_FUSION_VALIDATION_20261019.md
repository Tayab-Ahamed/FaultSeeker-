# Feature-fusion validation

## Protocol and leakage checks

- Population: 1,115 rows: 115 exploit and 1,000 benign traces.
- Same retained legacy inputs and labels as the original fusion experiment.
- Five folds assigned by `sha256(txn_hash) mod 5`.
- Every variant used the same fold assignments and examples.
- The threshold remained fixed at `0.5`; no test-row threshold selection was
  performed.
- Calibration scaling was fit on training rows only within each fold.
- Feature payloads were restricted to `txn_hash`, `chain`,
  `functioncall_count`, `address_count`, `max_depth`, and `gas_cost`; labels,
  vulnerability classes, and ground-truth fields were absent.
- All five variants were predeclared; no variant was selected using held-out
  results.

## Overall ablations

| Variant | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Eight-feature baseline | 72 | 10 | 990 | 43 | 0.8780 | 0.6261 | 0.7310 | 0.0100 | 0.035851 | 0.037711 |
| + static score | 74 | 10 | 990 | 41 | 0.8810 | 0.6435 | 0.7437 | 0.0100 | 0.035091 | 0.037912 |
| + dynamic score | 73 | 10 | 990 | 42 | 0.8795 | 0.6348 | 0.7374 | 0.0100 | 0.035812 | 0.038435 |
| + LLM score | 74 | 10 | 990 | 41 | 0.8810 | 0.6435 | 0.7437 | 0.0100 | 0.034556 | 0.034636 |
| Full fusion | 74 | 9 | 991 | 41 | 0.8916 | 0.6435 | 0.7475 | 0.0090 | 0.033944 | 0.036376 |

Paired comparisons against baseline:

| Variant | Baseline-only correct | Candidate-only correct | Discordant | χ² |
|---|---:|---:|---:|---:|
| + static score | 0 | 2 | 2 | 0.5000 |
| + dynamic score | 0 | 1 | 1 | 0.0000 |
| + LLM score | 1 | 3 | 4 | 0.2500 |
| Full fusion | 0 | 3 | 3 | 1.3333 |

## Per-fold baseline versus full fusion

| Fold | n | Variant | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Brier | ECE |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 224 | Baseline | 16 | 4 | 197 | 7 | 0.8000 | 0.6957 | 0.7442 | 0.0199 | 0.03621 | 0.03545 |
| 0 | 224 | Full fusion | 17 | 4 | 197 | 6 | 0.8095 | 0.7391 | 0.7727 | 0.0199 | 0.03411 | 0.03662 |
| 1 | 219 | Baseline | 14 | 0 | 195 | 10 | 1.0000 | 0.5833 | 0.7368 | 0.0000 | 0.03739 | 0.05899 |
| 1 | 219 | Full fusion | 14 | 0 | 195 | 10 | 1.0000 | 0.5833 | 0.7368 | 0.0000 | 0.03565 | 0.05440 |
| 2 | 211 | Baseline | 12 | 2 | 186 | 11 | 0.8571 | 0.5217 | 0.6486 | 0.0106 | 0.03903 | 0.06051 |
| 2 | 211 | Full fusion | 12 | 1 | 187 | 11 | 0.9231 | 0.5217 | 0.6667 | 0.0053 | 0.03670 | 0.05523 |
| 3 | 232 | Baseline | 13 | 2 | 210 | 7 | 0.8667 | 0.6500 | 0.7429 | 0.0094 | 0.03060 | 0.04704 |
| 3 | 232 | Full fusion | 14 | 2 | 210 | 6 | 0.8750 | 0.7000 | 0.7778 | 0.0094 | 0.02937 | 0.04822 |
| 4 | 229 | Baseline | 17 | 2 | 202 | 8 | 0.8947 | 0.6800 | 0.7727 | 0.0098 | 0.03643 | 0.05134 |
| 4 | 229 | Full fusion | 17 | 2 | 202 | 8 | 0.8947 | 0.6800 | 0.7727 | 0.0098 | 0.03424 | 0.03467 |

The gain is not concentrated in one fold: full fusion improves folds 0, 2,
and 3, is unchanged in folds 1 and 4, and improves Brier score in every fold.
However, only three examples change correctness overall, so no statistical
significance claim is made.

## Exact changed examples

The full-fusion variant changes three predictions:

| Transaction | Fold | Label | Trace features `(calls, addresses, depth, gas)` | Static | Dynamic | LLM | Baseline → Fusion |
|---|---:|---:|---|---:|---:|---:|---|
| `0x998f1da472d927e74405b0aa1bbf5c1dbc50d74b39977bed3307ea2ada1f1d3f` | 0 | 1 | `(43, 5, 7, 191309)` | 0.1800 | 0.2678 | 0.5264 | `0.4983 → 0.5196`, negative → positive |
| `0xeaef2831d4d6bca04e4e9035613be637ae3b0034977673c1c2f10903926f29c0` | 3 | 1 | `(126, 7, 5, 392041)` | 0.4825 | 0.3617 | 0.6620 | `0.4593 → 0.6135`, negative → positive |
| `0x7c33203421181fbe3bb5ced6add5fc8dbd770a48af37bac510bb8cdd7ad9ec30` | 2 | 0 | `(107, 28, 13, 658385)` | 0.4966 | 0.6638 | 0.8902 | `0.5624 → 0.4833`, positive → negative |

The first two are recovered exploit rows; the third is a false-positive
removal. Available evidence is limited to the retained trace-derived feature
vectors and component scores; no complete call tree is claimed for these rows.

## Decision

Full fusion remains the strongest experimental variant. It is not promoted to
the production default or used for the original 246-row claim because the
legacy cohort is historically exposed and only three correctness decisions
change. Independent validation requires a new immutable, trace-complete,
independently adjudicated cohort.

Evidence directory:

```text
reports/reproducibility/legacy_115_diagnostic/feature_fusion_validation/
```
