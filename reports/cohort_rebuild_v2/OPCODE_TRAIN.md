# Authentic train opcode replay

Two new accepted canonical captures: Rubic (668 SLOAD, 220 SSTORE) and Euler
(448 SLOAD, 95 SSTORE). Both passed signed transaction, exact prefix, receipt,
block environment, normalization and storage-owner checks. Actual counts and
hash-bound run records are in RPC_TRAIN_CONCLUSION.json.

Rubic succeeded after optional Anvil read methods were allowlisted and upstream
reads recovered. Its numeric-tag-only prestate cache had zero hits: the cache is
not credited for that success. Euler then served 147 observed exact-parent reads
using EIP-1898 parent-hash tags, with 17 actual upstream requests. Every unknown
field/slot still used the metered endpoint. No parent state value was guessed or
overridden. The cache is restricted to first-in-block, pre-Shanghai Ethereum.
The prestate source and canonical block/receipt are revalidated offline.

Run: python scripts/capture_authentic_opcodes.py --transaction TX_HASH --mine-timeout 180 --prestate-cache
Only frozen train members are authorized. Recorded captures are revalidated
without being overwritten. Earlier attempt indices are content-addressed under
opcode_history; the live train index preserves observations for unselected train
identities. It never overwrites the pre-freeze index.

These are two non-reentrancy-root-cause train cases. They do not establish
reentrancy F1, cohort-wide performance, native upstream opcode support, billed
inference savings, all-chain archive availability or independent-provider recovery.
Claim 25 remains UNVERIFIABLE at its full scope. No paper text was changed.

Prestate semantics: https://geth.ethereum.org/docs/developers/evm-tracing/built-in-tracers
Anvil account reads: https://foundry-rs.github.io/foundry/anvil/eth/api/struct.EthApi.html
