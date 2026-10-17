# Batch A Job 2 final report

**Label: producer-era replay, exploratory**

## Receipt cause

The original 21 unmatched receipt files were JSON-RPC responses with `result: null`. They contained no JSON-RPC error object and no rate-limit response. The 21 missing receipts were refetched from the public keyless endpoint using only `eth_getTransactionReceipt`, at approximately one request per second, with the saved refetch responses under `rpc_publicnode_receipt_refetch/eth/`. The refetched responses remained `result: null` for all 21 rows.

- Existing usable receipt pairs: 2
- Receipts refetched: 21
- Refetched receipt responses still null: 21
- Refetched receipt JSON-RPC errors: 0
- Refetched rate-limit responses: 0
- Paid/signup/API-key/card prompt: none

## Corrected verification gate

A row is verified only when:

1. `transaction.hash` equals the frozen Batch A transaction hash;
2. `receipt.transactionHash` equals that same hash;
3. transaction and receipt `blockNumber` values are equal; and
4. the transaction is not pending (`transaction.blockNumber` is present).

Results:

- Rows checked: 23
- Verified: 2
- Excluded: 21
- Exclusion reasons:
  - `receipt.transactionHash_mismatch`: 21
  - `transaction_receipt.blockNumber_mismatch`: 18
  - `transaction.hash_mismatch`: 3
  - `transaction.pending`: 3

Per-row returned hashes, block numbers, and reasons are in `job2_final_verification.json`.

## Producer-era replay

The unmodified producer-era path from commit `1b1c7395771663622dd14b9731b4b8b471221960` ran once for the 2 verified rows. Scoring used the current unchanged localization scorer with its existing `code_address` fallback. No ranker, scorer, or weights were edited.

The verified sample is **too small to read** (`N=2`, below 10).

| Metric | R@1 | R@3 | R@5 | N |
| --- | ---: | ---: | ---: | ---: |
| Primary address+function | 0/2 (0.000000) | 0/2 (0.000000) | 0/2 (0.000000) | 2 |
| Function-only sensitivity | 0/2 (0.000000) | 0/2 (0.000000) | 0/2 (0.000000) | 2 |
| Address-only sensitivity | 1/2 (0.500000) | 1/2 (0.500000) | 1/2 (0.500000) | 2 |

Candidate counts: 2 rows, minimum 10, maximum 32, mean 21.0.

Full scoring output: `producer_batchA_measurement_final.json` and `producer_batchA_measurement_final.md`.
