# TRAIN localization source evidence

Acquisition only: frozen labels, manifests, split, and heldout partition were not modified or scored.

| Incident | Publisher-supported function | Verified selector | Historical code address | Storage address / call |
|---|---|---|---|---|
| reviewed:Euler Finance | `donateToReserves(uint256,uint256)` | `0x36f022aa` | `0xbb0d4bb654a21054af95456a3b29c63e8d1f4c0a` | `0x27182842e098f60e3d576794a5bffb0777e025d3` / DELEGATECALL |
| reviewed:Revest Finance | `depositAdditionalToFNFT(uint256,uint256,uint256)` | `0x5dcb7ab2` | `0x2320a28f52334d62622cc2eafa15de55f9987ed9` | `0x2320a28f52334d62622cc2eafa15de55f9987ed9` / CALL |

All eight queried contract responses returned Sourcify `runtimeMatch=exact_match`; their returned onchain runtime bytecode exactly equals the captured historical prestate bytecode. Function names come from frozen publisher observations; signatures and selectors come only from those verified ABIs. The full Sourcify responses contain Solidity source content, compilation settings, ABI, and bytecode. SHA-256 bindings and request URLs are in `evidence.json` and `http/*.json`.

Euler has independent BlockSec and PeckShield observations naming donateToReserves. Revest has a SlowMist reentrancy mechanism observation and a BlockSec observation naming depositAdditionalToFNFT. These are attributed public-source observations, not independent human annotations.

Euler executes the function code through DELEGATECALL: source code address and storage address differ. Its matching normalized opcode frame has four storage events belonging to the reported storage owner. The Revest matching CALL has no direct storage events in that exact frame; its presence is established by the historical call trace. Both historical opcode captures are SHA-256 bound, transaction-identity checked, and normalization-complete.

No vulnerable line targets are asserted. A verified function declaration or source map alone would not establish which source line is the root cause. Sourcify verification is an external attestation; this acquisition did not independently rebuild the compiler output.

Request accounting: 19 public request attempts total: one successful documentation lookup through the web tool, nine sandbox DNS failures (documentation plus eight contract endpoints), then nine successful public GET retries after sandbox escalation. No RPC calls, paid APIs, package operations, or additional source searches. Original DNS-failure bodies and metadata remain as `.attempt1.*`; final successful response bodies are cached and SHA-256 checked. The final reproducibility run used zero network requests.

Validation: tests were created first and initially failed because the implementation module did not exist. All four parser/validator tests then passed. `python scripts/acquire_train_localization_sources.py` rebuilt the report from cached responses with zero HTTP requests. Root owns the full suite and integration gate.

The candidate list is a bounded set of actual historical trace destinations, not an exhaustive source search. It was selected without model output or heldout outcomes. Ground truth function identities remain frozen and unavailable to the scored evaluator until a separately authorized, versioned protocol admits this new evidence.
