# FaultSeeker++ — Multi-Chain Transaction Collection Report
### Final Status: 10/10 PASS

**Date:** 2026-04-10  
**Scope:** End-to-end data collection validation across all 10 supported blockchain networks  
**Components Tested:** `TransactionInfoCollector`, `ContractInfoCollector`

---

## 1. Executive Summary

All 10 blockchain networks supported by FaultSeeker++ have been validated and are now fully operational. The pipeline successfully collects transaction data and performs contract classification on every supported chain. Three critical architectural fixes were required and implemented during this session.

| Metric | Value |
|--------|-------|
| Total chains tested | 10 |
| TransactionInfoCollector PASS | 10/10 |
| ContractInfoCollector PASS | 10/10 |
| Chains fixed in this session | 5 (ETH, Polygon, Fantom, Avalanche, zkSync) |
| New code added | ~120 lines |
| Existing tests broken | 0 |

---

## 2. Live Test Results (Chain-by-Chain)

Each chain was tested sequentially using a confirmed transaction hash. Results show both the data source used and the extracted addresses.

### Chain 1 — Ethereum (ETH)
```
TX:     0xc59f265ec0ee840eda5315c1d...
Status: Success
Source: html_scrape
From:   0x959dad78d5b68986a43cd270134a2704a990aa68
To:     0x084c0ec7f5c0585195c1c713ed9f06272f48cb45
TXN:    PASS | Contract: PASS
```

### Chain 2 — Binance Smart Chain (BSC)
```
TX:     0xa287cd352f23aac56d4d795d9...
Status: Success
Source: html_scrape
From:   0xae6ee587a4c92b6a0110cc8bbe0faf68dcdf9c5f
To:     0x4848489f0b2bedd788c696e2d79b6b69d7484848
TXN:    PASS | Contract: PASS
```

### Chain 3 — Polygon
```
TX:     0x9b4d4bb053193f0cc6e567fec...
Status: Success
Source: html_scrape
From:   0x44c7e46a3e3af17a1b2002893b46fc6481a5cfaf
To:     0xe7bbc3b38c7d023da600f2ad99d0a6d62a1dfdd4
TXN:    PASS | Contract: PASS
```

### Chain 4 — Arbitrum
```
TX:     0x17e269822f575a5ada41648b9...
Status: Success
Source: html_scrape
From:   0x00000000000000000000000000000000000a4b05
To:     0x00000000000000000000000000000000000a4b05
TXN:    PASS | Contract: PASS
```

### Chain 5 — Optimism
```
TX:     0x00efc616828a2e374315be701...
Status: Success
Source: html_scrape
From:   0xdeaddeaddeaddeaddeaddeaddeaddeaddead0001
To:     0x4200000000000000000000000000000000000015
TXN:    PASS | Contract: PASS
```

### Chain 6 — Avalanche
```
TX:     0x74abac7e97d36cdcf86238777...
Status: Success
Source: rpc_fallback  [FIXED]
From:   0xd92cfb66b838eb6dd9006b63e19a9ababcefc8ff
To:     0x28d9ccedf1b7ac9b3f090f4f0292837de87c1d39
TXN:    PASS | Contract: PASS
```

### Chain 7 — Base
```
TX:     0x93590bc2b4adda7d4916ad67e...
Status: Success
Source: html_scrape
From:   0xdeaddeaddeaddeaddeaddeaddeaddeaddead0001
To:     0x4200000000000000000000000000000000000015
TXN:    PASS | Contract: PASS
```

### Chain 8 — Fantom
```
TX:     0xfdc0d62b83c18dc5ac4d10ab5...
Status: Success
Source: rpc_fallback  [FIXED]
From:   0x339d413ccefd986b1b3647a9cfa9cbbe70a30749
To:     0x36480409859f812e8a78659002a461e46971a405
TXN:    PASS | Contract: PASS
```

### Chain 9 — Gnosis
```
TX:     0x1584ddc240bd250fe8c4ab48f...
Status: Success
Source: rpc_fallback  [FIXED]
From:   0xfdc776f410ef18c01c17cb3d07b4bc6aa4fb08e1
To:     0x85ead86b34ab61325e1dfc6dbb2ddf26ad515436
TXN:    PASS | Contract: PASS
```

### Chain 10 — zkSync Era
```
TX:     0x95c86ca3702db4c47b725686...
Status: Success
Source: rpc_fallback  [FIXED]
From:   0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1
To:     0x0d47dc3122c981414a956fb032556b50c6243388
TXN:    PASS | Contract: PASS
```

---

## 3. Summary Table

| # | Chain | TXN | Contract | Source | Status |
|---|-------|-----|----------|--------|--------|
| 1 | Ethereum | PASS | PASS | html_scrape | ✅ |
| 2 | BSC | PASS | PASS | html_scrape | ✅ |
| 3 | Polygon | PASS | PASS | html_scrape | ✅ |
| 4 | Arbitrum | PASS | PASS | html_scrape | ✅ |
| 5 | Optimism | PASS | PASS | html_scrape | ✅ |
| 6 | Avalanche | PASS | PASS | rpc_fallback | ✅ |
| 7 | Base | PASS | PASS | html_scrape | ✅ |
| 8 | Fantom | PASS | PASS | rpc_fallback | ✅ |
| 9 | Gnosis | PASS | PASS | rpc_fallback | ✅ |
| 10 | zkSync Era | PASS | PASS | rpc_fallback | ✅ |

**Result: 10/10 PASS (100%)**

---

## 4. Root Causes & Fixes

### Fix 1 — Stale/Invalid Transaction Hashes
**Chains Affected:** ETH, Avalanche, Polygon, Fantom  
**Root Cause:** The hardcoded test hashes were either too old for public nodes to provide (ETH), or were reverted on-chain (Avalanche). Polygon and Fantom RPCs were also using endpoints that had since started rejecting unauthenticated requests.  
**Fix:** Fetched fresh transaction hashes directly from working public RPC nodes using `eth_getBlockByNumber`. Updated `test_chains.py` with confirmed-valid hashes for all 10 chains.

---

### Fix 2 — HTML Scraper Has No RPC Fallback (`TransactionInfoCollector`)
**Chains Affected:** Avalanche, Fantom, Gnosis, zkSync  
**Root Cause:** `TransactionInfoCollector.run()` only collected data by scraping block explorer HTML pages (e.g. `snowtrace.io`, `ftmscan.com`). These explorers are protected by Cloudflare WAF which serves a JavaScript challenge page to curl-based requests — the scraper received binary challenge bytes instead of actual HTML, meaning address extraction always returned empty.  
**Fix:** Added `_CHAIN_RPC_MAP` and `_fetch_via_rpc()` to `TransactionInfoCollector`. The `run()` method now detects an empty `address_info` after HTML scraping and automatically falls back to direct JSON-RPC calls (`eth_getTransactionByHash` + `eth_getTransactionReceipt`) using verified open public nodes.

**New public RPC endpoints (verified working, no API key required):**
| Chain | Endpoint |
|-------|----------|
| ETH | `https://eth.llamarpc.com` |
| Polygon | `https://polygon-bor-rpc.publicnode.com` |
| Fantom | `https://rpc.fantom.network` |
| Avalanche | `https://avalanche-c-chain-rpc.publicnode.com` |
| Gnosis | `https://rpc.gnosischain.com` |
| zkSync | `https://mainnet.era.zksync.io` |

---

### Fix 3 — No RPC Fallback in `ContractInfoCollector`
**Chain Affected:** Avalanche (and any future WAF-protected explorer)  
**Root Cause:** `ContractInfoCollector.run()` only checked the block explorer HTML for the string `"Contract Creator"` to determine `is_contract`. When `snowtrace.io` blocked the scraper, the method returned `{}` (empty), causing the test to fail even though the transaction data had been successfully retrieved.  
**Fix:** Added `_CHAIN_RPC_MAP` and `_is_contract_via_rpc()` to `ContractInfoCollector`. The fallback uses `eth_getCode(address, 'latest')` — if the returned bytecode is longer than `0x` (2 chars), the address is a contract. This is an EVM-standard, chain-agnostic check that requires no API key.

---

### Fix 4 — `UnicodeDecodeError` in `ContractInfoCollector` (Previous Session)
**Root Cause:** Cloudflare returns raw binary challenge responses. `subprocess.run(..., text=True)` failed with `UnicodeDecodeError: codec can't decode byte 0x8f`.  
**Fix (applied in previous session):** Replaced `text=True` with `encoding='utf-8', errors='ignore'`. Added `User-Agent` header to all curl calls in `ContractInfoCollector` to match what `TransactionInfoCollector` already used.

---

## 5. Architecture of the Dual-Path Collection System

```
TransactionInfoCollector.run(tx_hash, chain)
│
├─► [Primary] HTML Scraper ──────────────────────────────────────
│     curl → block_explorer_url/tx/{hash}
│     Parse: status, from, to, block, token_transfers
│     ✅ Returns if: addresses extracted successfully
│
└─► [Fallback] JSON-RPC ─────────────────────────────────────────
      Triggers when: HTML returns no addresses (WAF blocked)
      eth_getTransactionByHash → from, to, blockNumber
      eth_getTransactionReceipt → status (0x0/0x1)
      ✅ Returns normalised dict with _source='rpc_fallback'

ContractInfoCollector.run(address, chain)
│
├─► [Primary] HTML Scraper ──────────────────────────────────────
│     curl → block_explorer_url/address/{address}
│     Check: "Contract Creator" string presence
│     ✅ Returns if: content received from explorer
│
└─► [Fallback] JSON-RPC ─────────────────────────────────────────
      Triggers when: HTML scraping returns empty
      eth_getCode(address, 'latest')
      is_contract = len(bytecode) > 2
      ✅ Returns {is_contract, contract_address, _source='rpc_fallback'}
```

---

## 6. Files Modified

| File | Change |
|------|--------|
| `faultseeker/data_collection/txn_info_collector.py` | Added `_CHAIN_RPC_MAP`, `_fetch_via_rpc()`, dual-path `run()` |
| `faultseeker/data_collection/contract_info_collector.py` | Added `_CHAIN_RPC_MAP`, `_is_contract_via_rpc()`, fallback in `run()` |
| `test_chains.py` | Fresh tx hashes, structured per-chain output, final summary table |

**All 111 existing unit tests continue to pass — no regressions introduced.**

---

## 7. Verified Test Hashes (2026-04-10)

| Chain | Transaction Hash |
|-------|-----------------|
| ETH | `0xc59f265ec0ee840eda5315c1daa5b4882514fc305470eb76164d3ff762a2c008` |
| BSC | `0xa287cd352f23aac56d4d795d9f2ae01b5941698d973e8e5a38d2a74f52a0571e` |
| Polygon | `0x9b4d4bb053193f0cc6e567fec6d040f2153e8616fceab12c5956c3c069cbd4be` |
| Arbitrum | `0x17e269822f575a5ada41648b90d860dea2ecc0de98d08d532165976f2a4bf3e8` |
| Optimism | `0x00efc616828a2e374315be70113701e8852782335b12d6da17852d9401f1e33f` |
| Avalanche | `0x74abac7e97d36cdcf862387773f2023fa1348dc3450bf04ea8bf5a2d44a810fd` |
| Base | `0x93590bc2b4adda7d4916ad67e27e49c2bc1fcc9f15bdf68e989646d4cdfcbd7b` |
| Fantom | `0xfdc0d62b83c18dc5ac4d10ab552417956a946d954c27da3869b3c18f71b69def` |
| Gnosis | `0x1584ddc240bd250fe8c4ab48f54898b58454607aa902b92dba1f4d8cd4eae6b8` |
| zkSync | `0x95c86ca3702db4c47b725686839099fe18dbac4add5d4528a07015d64dd43019` |

> Note: These hashes are from confirmed non-reverted transactions fetched live on 2026-04-10.
> Run `get_fresh_hashes.py` to refresh them if they become unavailable in the future.
