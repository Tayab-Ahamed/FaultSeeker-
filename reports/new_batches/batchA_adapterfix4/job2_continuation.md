# Batch A adapter fix 4 — Job 2 continuation

**Label: producer-era replay, exploratory**

Fetch completed using only `eth_getTransactionByHash` and `eth_getTransactionReceipt` against `https://ethereum.publicnode.com`, with 1 request/second pacing. Two complete dRPC pairs were reused; 21 remaining transaction/receipt call pairs were issued.

- Rows checked: 23
- New transactions fetched: 21
- Complete dRPC pairs reused: 2
- Rows with matching returned transaction hash: 20
- Rows with matching returned receipt transaction hash: 2
- Rows with matching transaction/receipt block numbers: 5
- Frozen Batch A records containing an expected block number: 0
- Rows excluded: 23
- Rows replayed: 0

Verification found no expected `block_number` or `blockNumber` field in the frozen Batch A records. Every row was therefore excluded with reason `batch_record.blockNumber` missing. No producer-era replay or scoring run was executed; no verification rule was adapted.

Raw one-file-per-transaction responses: `reports/new_batches/batchA_adapterfix4/rpc_publicnode_raw/eth/`.
