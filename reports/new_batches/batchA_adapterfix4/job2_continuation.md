# Batch A adapter fix 4 — Job 2 continuation

**Label: producer-era replay, exploratory**

Fetch completed using only `eth_getTransactionByHash` and `eth_getTransactionReceipt` against the public keyless endpoint. Two complete dRPC pairs were reused; the remaining 21 transaction/receipt pairs were fetched with 1 request/second pacing.

Verification found no expected `block_number` or `blockNumber` field in the frozen Batch A records. Every row was therefore excluded with reason `batch_record.blockNumber` missing. No producer-era replay or scoring run was executed; no verification rule was adapted.

Raw one-file-per-transaction responses: `reports/new_batches/batchA_adapterfix4/rpc_publicnode_raw/eth/`.
