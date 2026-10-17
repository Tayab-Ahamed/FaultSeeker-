# Batch A dRPC final replay

**Label: producer-era replay, exploratory**

The configured dRPC endpoint passed one read-only `eth_blockNumber` call. No paid-plan, billing, upgrade, card, or limit message was returned.

## Fetching and verification

- Complete pairs reused: 2
- Remaining transactions fetched from dRPC: 21
- Methods used: `eth_getTransactionByHash`, `eth_getTransactionReceipt`
- Request pacing: approximately 2 requests/second
- Paid/limit stop: not triggered
- Rows checked: 23
- Verified: 23
- Excluded: 0
- Exclusion reasons: none

The verification gate was:

1. returned transaction `hash` equals the frozen Batch A hash;
2. receipt `transactionHash` equals the same hash;
3. transaction and receipt `blockNumber` values are equal; and
4. the transaction is not pending.

Raw dRPC responses are under `rpc_drpc_final/eth/`. Per-row verification, including the recorded block numbers, is in `job2_drpc_verification_final.json`.

## Producer-era replay, exploratory

- Producer commit: `1b1c7395771663622dd14b9731b4b8b471221960`
- Producer-era orchestration: unmodified
- Current scorer: unchanged; includes the existing `code_address` fallback
- Verified sample: 23 rows
- Sample too small to read: no

| Metric | R@1 | R@3 | R@5 | N |
| --- | ---: | ---: | ---: | ---: |
| Primary address+function | 0/23 (0.000000) | 0/23 (0.000000) | 0/23 (0.000000) | 23 |
| Function-only sensitivity | 0/23 (0.000000) | 0/23 (0.000000) | 0/23 (0.000000) | 23 |
| Address-only sensitivity | 1/23 (0.043478) | 18/23 (0.782609) | 20/23 (0.869565) | 23 |

Candidate counts:

- Rows: 23
- Minimum: 4
- Maximum: 88
- Mean: 15.826087

Machine-readable output: `job2_drpc_final_report.json` and `producer_batchA_measurement_drpc_final.json`.
