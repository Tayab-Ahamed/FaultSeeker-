# Batch C phase 1 protocol

**Status: pre-registered before any tracing or scoring.** This phase freezes the dataset and protocol only. It performs no RPC, no node tracing, no scoring, and no ranker invocation.

## Scope and provenance

- Label: **Batch C, single-chain Ethereum mainnet, DeFiHackLabs-sourced**.
- Source repository: `https://github.com/SunWeb3Sec/DeFiHackLabs`.
- Every retained raw source file is pinned to commit `7363f76db51f0fea97f8e659b20ee8bdc5fbca25` and has a recorded URL, UTC fetch date, one-request fetch record, and SHA-256 content hash in `source_manifest.json`.
- Selection uses only source-backed incident identity, Ethereum-mainnet provenance, year/category coverage, explicit vulnerable address, externally callable target, and complete source-resolved typed signature.
- Batch C excludes every transaction in the 115 ground-truth JSONs, the 110 benchmark rows, all Batch A transactions, and all Batch B transactions, including Batch B's later excluded trace row.
- Batch B results, Batch B ranker output, and any other ranker/scoring output were not read or used to choose Batch C rows.
- At most one transaction is retained per incident.

## Selection requirements

The frozen set contains at least 30 distinct Ethereum-mainnet incidents spread across years and vulnerability categories. A row is eligible only when:

1. The fetched PoC contains one explicit Ethereum-mainnet transaction hash and a source-backed vulnerable contract address.
2. The target is externally callable, not an internal-only helper, low-level selector, or unresolved proxy-only placeholder.
3. The PoC source (or a locally fetched, pinned source file imported by that PoC) provides a complete argument-typed signature.
4. The transaction hash, vulnerable address, and signature evidence are quoted with exact source file paths and one-based lines.
5. The transaction hash and address do not intersect any frozen exclusion set.

Types are never inferred. Rows failing any condition are excluded with a reason in `exclusions.json` and `REPORT.md`.

## Frozen row schema

Each row in `batchC_candidates.json` records the transaction hash, incident name and month, Ethereum chain, PoC file, pinned commit, raw source URL, vulnerable contract address, canonical full signature, keccak256 4-byte selector, vulnerability category, and exact line quotes for the transaction, address, signature declaration, and PoC call. Evidence entries include the source file path and one-based line.

## Future verification and scoring

Batch C stays sealed: **no tracing and no scoring until the ranker upgrade work is finished and its commit hash is recorded.**

After the seal is opened, score once with the final ranker version only. The protocol is:

- Primary key: vulnerable contract address + full-signature selector.
- Sensitivity keys: address-only and selector-only.
- Metrics: R@1, R@3, and R@5 for each key, with Wilson 95% intervals.
- No tuning, retuning, ranker changes, scorer changes, weight changes, Batch C-specific heuristics, or partial-result peeking.
- Use the same verification gate as Batch B: matching transaction and receipt hashes, matching block numbers, non-pending transaction, and valid full trace before a row enters N.

The protocol stops at this phase-1 freeze. No RPC, tracing, scoring, or ranker invocation is permitted during phase 1.
