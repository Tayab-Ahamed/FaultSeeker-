# Batch B phase 2 report

**Batch B, pre-registered, one-shot, ETH only, DeFiHackLabs-sourced**

Tracing used only the configured HTTPS dRPC endpoint with one attempt per method, approximately two requests per second, and the three pre-authorized JSON-RPC methods. No publicnode, account creation, key output, retry, tuning, or partial-result peeking was used.

Frozen Batch B SHA-256: `5b66ae6d8c2b6bc23fbdb03f82738ada4684865846f2792d5111edc92cee942a`
Producer commit: `1b1c7395771663622dd14b9731b4b8b471221960`
Run directory: `run_20261017T180610Z`

## Verification

- Rows attempted: **20**
- Verified: **19**
- Excluded: **1**
- Paid-plan/limit stop: **None**

| Transaction | Incident | Status | Reason |
| --- | --- | --- | --- |
| `0xae7d664bdf…` | Lendf.Me | verified | — |
| `0x4643b63dcb…` | Bancor | verified | — |
| `0xcd7dae143a…` | Popsicle Finance | verified | — |
| `0x4227bca8ed…` | Audius governance takeover | verified | — |
| `0xa5fe9d044e…` | Nomad Bridge | verified | — |
| `0x04b166e7b4…` | Sushi RouteProcessor2 | verified | — |
| `0xeb87ebc0a1…` | Sturdy Finance | verified | — |
| `0xcff84cc137…` | Compounder Finance | verified | — |
| `0xa84aa065ce…` | Curve Vyper reentrancy 1 | verified | — |
| `0x2e7dc8b2fb…` | Curve Vyper reentrancy 2 | verified | — |
| `0x00b375f8e9…` | 0x0 Privacy DEX | verified | — |
| `0xede72a74d8…` | CEXISWAP | verified | — |
| `0x726459a468…` | GoodDollar | verified | — |
| `0xe0bada18fd…` | Orbit Chain | verified | — |
| `0x903d88a92c…` | XBridge | verified | — |
| `0x8b74995d1d…` | Conic Finance | verified | — |
| `0xd9fdc7d03e…` | SASHA token | verified | — |
| `0x103b4550a1…` | 0xf340 | verified | — |
| `0x1438ff9dd1…` | Li.Fi | excluded | transaction.hash_mismatch; receipt.transactionHash_mismatch; transaction.pending; trace.invalid_or_missing_callTracer_result; trace.rpc_error; request.failed:debug_traceTransaction |
| `0x7ac4a98599…` | Wise Lending | verified | — |

The excluded Li.Fi trace request returned the exact dRPC error text `transaction not found`; its transaction and receipt were also not verified, so it was not scored.

## One-shot replay and scoring

- Verified scoring N: **19**
- Producer-era ranker invocations: **19**
- Scoring passes: **1**
- Tuning: **False**
- Partial-result peeking: **False**

| Key | R@1 | R@3 | R@5 |
| --- | ---: | ---: | ---: |
| Address + selector (primary) | 3/19 (0.157895) | 4/19 (0.210526) | 5/19 (0.263158) |
| Address-only sensitivity | 3/19 (0.157895) | 8/19 (0.421053) | 11/19 (0.578947) |
| Selector-only sensitivity | 3/19 (0.157895) | 4/19 (0.210526) | 5/19 (0.263158) |

Candidate counts: N=19, min=2, max=290, mean=73.578947.

| Tx prefix | Candidates | Address+selector | Address-only | Selector-only |
| --- | ---: | ---: | ---: | ---: |
| `0xae7d664bdf…` | 19 | 18 | 5 | 18 |
| `0x4643b63dcb…` | 2 | 1 | 1 | 1 |
| `0xcd7dae143a…` | 290 | 65 | 65 | 65 |
| `0x4227bca8ed…` | 8 | 2 | 2 | 2 |
| `0xa5fe9d044e…` | 14 | 1 | 1 | 1 |
| `0x04b166e7b4…` | 9 | 1 | 1 | 1 |
| `0xeb87ebc0a1…` | 285 | 176 | 48 | 176 |
| `0xcff84cc137…` | 78 | 67 | 42 | 67 |
| `0xa84aa065ce…` | 25 | 10 | 6 | 9 |
| `0x2e7dc8b2fb…` | 21 | 9 | 3 | 9 |
| `0x00b375f8e9…` | 71 | None | None | 37 |
| `0xede72a74d8…` | 8 | None | 2 | None |
| `0x726459a468…` | 117 | 68 | 68 | 68 |
| `0xe0bada18fd…` | 7 | 4 | 4 | 4 |
| `0x903d88a92c…` | 8 | 7 | 5 | 6 |
| `0x8b74995d1d…` | 248 | 175 | 114 | 175 |
| `0xd9fdc7d03e…` | 21 | 15 | 15 | 15 |
| `0x103b4550a1…` | 15 | 6 | 2 | 6 |
| `0x7ac4a98599…` | 152 | 28 | 3 | 28 |

Raw responses, attempts, stderr, verification rows, and full saved candidate lists are under the run directory. No production ranker/scorer/weights, frozen Batch B data, existing results, or Batch A artifacts were modified.
