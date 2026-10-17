# Batch B phase 1 protocol

**Status: pre-registered before tracing.**  This phase freezes the dataset and protocol only. It performs no RPC, no node tracing, and no scoring.

## Scope and provenance

- Label: **Batch B, single-chain Ethereum mainnet, DeFiHackLabs-sourced**.
- Source repository: `https://github.com/SunWeb3Sec/DeFiHackLabs`.
- All PoC files are pinned to commit `7363f76db51f0fea97f8e659b20ee8bdc5fbca25`.
- Selection is based only on incident diversity, source-backed provenance, chain, date, category, and signature availability. It is not selected by predicted ranker behaviour.
- Batch B excludes every transaction in the 115 ground-truth JSON records, the 110 benchmark rows, and Batch A.
- At most one transaction is retained per incident.

## Selection requirements

The frozen set must contain at least 20 distinct Ethereum-mainnet incidents, spread across years and protocol/vulnerability types, including representation from lending, DEX/swap, bridge, token, access control, price/oracle, reentrancy, and other available categories. A row is eligible only when:

1. The PoC identifies the transaction hash and vulnerable contract address.
2. The vulnerable target is externally callable, not an internal-only helper.
3. The PoC provides a complete argument-typed function signature in an interface declaration or an explicit PoC call line.
4. The transaction hash and vulnerable contract address match the row's source evidence exactly.

Rows failing any condition are excluded and recorded with a reason. Types are never inferred.

## Frozen row schema

Each row in `batchB_candidates.json` records the transaction hash, incident name and incident date, Ethereum chain, PoC file, pinned commit, source URL, vulnerable contract address, full canonical signature, keccak256 4-byte selector, exact source line quotes, and vulnerability category.

## Future tracing and evaluation

When node access is available, tracing will use the producer-era replay implementation at commit `1b1c7395771663622dd14b9731b4b8b471221960` and one scoring run only.

- Primary scoring key: vulnerable contract address + full-signature selector.
- Sensitivity keys: address-only and selector-only.
- Report R@1, R@3, and R@5 for each key, with N equal to the frozen verified set.
- No tuning, retuning, ranker changes, scorer changes, weight changes, or Batch B-specific heuristics.
- Do not inspect or use partial results to alter the dataset, protocol, or implementation.
- A trace is verified only when the transaction hash and receipt transaction hash are equal, the transaction and receipt block numbers are equal, and the transaction is not pending. Full ETH trace and receipt history are required.

The future run is a single-chain, DeFiHackLabs-sourced evaluation. Phase 1 stops after the dataset freeze and hash recording.
