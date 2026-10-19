# Recovered-trace localization experiment

Exploratory four-row paired comparison. No new RPC requests were made; no Batch B/C or Batch E results were read.

## Preregistered experiment

Adding generic observed call-tree address/selector candidates and a fixed trace-evidence-only rank will improve exact localization coverage without using target labels.

Treatment candidates are generated generically from observed call addresses and raw calldata selectors. Ground-truth function registration is disabled; only the public selector cache is available.

| System | N | Address coverage | Exact-function coverage | R@1 | R@3 | R@5 |
|---|---:|---:|---:|---:|---:|---:|
| Baseline saved predictions | 4 | 4/4 | 2/4 | 0/4 | 0/4 | 0/4 |
| Trace-aware fixed weight | 4 | 4/4 | 3/4 | 0/4 | 0/4 | 0/4 |

## Per-row changes

| Stable ID | Baseline function rank | Trace-aware function rank | Baseline address rank | Trace-aware address rank |
|---|---:|---:|---:|---:|
| `eth:0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb` | absent | absent | 32 | 32 |
| `eth:0x958236266991bc3fe3b77feaacea120f172c0708ad01c7a715b255f218f9313c` | 19 | 19 | 19 | 19 |
| `eth:0xa6f63fcb6bec8818864d96a5b1bb19e8bd85ee37b2cc916412e720988440b2aa` | 7 | 59 | 7 | 36 |
| `eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d` | absent | 46 | 3 | 8 |

Decision: **exploratory only; not production adopted and not a generalization claim**.

Machine-readable artifact: `reports/research_results/recovered_trace_localization_20261019.json`.
