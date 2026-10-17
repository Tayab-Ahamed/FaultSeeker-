# Batch B phase 1 report

**Frozen: 20 distinct Ethereum-mainnet incidents, DeFiHackLabs-sourced.**

No RPC, node tracing, scoring, ranker invocation, or result-file change was performed. Selection used source-backed incident diversity only, not ranker behaviour.

Pinned source commit: `7363f76db51f0fea97f8e659b20ee8bdc5fbca25`
Frozen canonical JSON SHA-256: `5b66ae6d8c2b6bc23fbdb03f82738ada4684865846f2792d5111edc92cee942a`

## Counts by vulnerability category

| Category | Count |
| --- | ---: |
| Access Control | 2 |
| Bridge Exploit | 3 |
| Bridge Exploit / Arbitrary Call | 1 |
| DEX / Arbitrary Call | 1 |
| DEX / Flash Loan | 1 |
| Delegatecall Abuse / Access Control | 1 |
| Governance Attack | 1 |
| Lending / Inflation Attack | 1 |
| Lending / Oracle Manipulation | 1 |
| Price Manipulation / Flash Loan | 1 |
| Reentrancy | 3 |
| Reentrancy / Business Logic | 1 |
| Reentrancy / Flash Loan | 1 |
| Reentrancy / Oracle Manipulation | 1 |
| Token / Price Manipulation | 1 |

## Counts by incident month

| Month | Count |
| --- | ---: |
| 2020-04 | 1 |
| 2020-06 | 1 |
| 2021-08 | 1 |
| 2022-03 | 1 |
| 2022-07 | 1 |
| 2022-08 | 1 |
| 2023-04 | 1 |
| 2023-06 | 2 |
| 2023-07 | 3 |
| 2023-09 | 2 |
| 2023-10 | 1 |
| 2023-12 | 1 |
| 2024-01 | 1 |
| 2024-04 | 1 |
| 2024-10 | 1 |
| 2025-08 | 1 |

## Exclusions

| File | Incident | Reason |
| --- | --- | --- |
| `Cream_exp.sol` | Cream | No explicit attack transaction hash; the candidate hash appears as a TOKENS_RECIPIENT_INTERFACE_HASH constant, not a PoC transaction URL. |
| `TeamFinance_exp.sol` | TeamFinance | The target migrate/lock interface is imported from interface.sol; the fetched PoC does not provide a complete locally source-resolved target signature. |
| `HundredFinance_2_exp.sol` | Hundred Finance 2 | PoC setUp forks Optimism, not Ethereum mainnet. |
| `Pawnfi_exp.sol` | Pawnfi | The vulnerable-contract comment address does not match the ApeStaking target addresses actually used by the PoC; contract-address match is ambiguous. |
| `PestoToken_exp.sol` | PestoToken | Vulnerable Contract field is blank, so no source-backed vulnerable contract address can be recorded. |
| `MEV_0xa247_exp.sol` | MEV 0xa247 | The exploit uses low-level calls with raw selectors and internal helper functions; no complete externally callable typed target signature is provided. |
| `UwuLend_First_exp.sol` | UwuLend | The vulnerable lending interface is imported from interface.sol and is not source-resolved in the fetched PoC; types are unresolved. |
| `Sonne_exp.sol` | Sonne | PoC setUp forks Optimism, not Ethereum mainnet. |
| `Orion_exp.sol` | Orion Protocol | The source transaction is already present in the excluded 110 benchmark rows. |

The exclusion scan used 115 local ground-truth JSON hashes, 110 local provider-pinned benchmark rows, and all Batch A transaction hashes. No frozen Batch B transaction intersected those sets.

## What tracing needs later

- A node/provider with full Ethereum mainnet execution traces for each frozen transaction and receipt history.
- Receipt transaction hash, transaction block number, and receipt block number for verification; pending or mismatched records are excluded.
- The provider key must remain outside chat and outside the repository. Phase 1 does not request or use it.
- The future run follows `PROTOCOL.md`: one producer-era replay at commit `1b1c739`, one scoring run, address+selector primary, address-only and selector-only sensitivity, R@1/3/5, and no Batch B tuning or partial-result peeking.
