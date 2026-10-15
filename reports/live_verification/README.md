# dRPC and compiled EVM verification — 2026-10-15

This is local compiler/EVM execution evidence and a bounded Ethereum access
check. It does not verify historical incident labels or published statistics.

## Real compiled execution

Official Foundry 1.8.5 and Solidity 0.8.30 binaries were downloaded into ignored
`build/tools`; their SHA-256 values matched official release metadata. Sources
were compiled, six contracts deployed on an ephemeral Anvil chain (31337), and
three transactions executed with both call and opcode tracing.

| Case | Opcodes | SLOAD | SSTORE | Paper score | Tier |
| --- | ---: | ---: | ---: | ---: | --- |
| Vulnerable recursive withdrawal | 1204 | 15 | 6 | 1.00 | CONFIRMED_REENTRANCY |
| Mutex-blocked nested withdrawal | 835 | 8 | 5 | 0.35 | POSSIBLE_REENTRANCY |
| Proxy delegatecall | 201 | 1 | 1 | 0.00 | NOT_REENTRANCY |

All three traces normalize completely. The mutex transitions are 1→2→1, and
delegatecall writes belong to the proxy. The rejected nested call is preserved
in raw evidence and excluded from successful-reentry signals.

**Measured limitation:** the guarded case remains a false positive at the paper's
unchanged detection threshold of 0.30. Filtering its mutex and failed callback
does not remove the other 0.35 of scoring evidence. No weight, threshold, input,
or paper text was adjusted to hide this result. These three designed examples
do not estimate population precision or recall.

Raw data: `compiled_evm_trace.json`. Hashes, counts, tool versions and access
results: `session_summary.json`.

## Live dRPC boundary

The configured endpoint returned Ethereum chain ID 1, block number 26194322,
and a historical benchmark transaction's receipt and call trace. Both default
opcode-trace attempts and an explicit empty-tracer attempt returned HTTP 400,
with the final response stating that
the `tracer` parameter is required. Opcode/SLOAD capture from this dRPC endpoint
has therefore **not** been demonstrated.

Seven requests reached dRPC. At the published flat price of $6 per million
requests, their conservative estimated upper cost is $0.000042, counting failed
requests and the chain-ID request as billable. Account billing was not queried;
this is an estimate, not a receipt. No model-provider calls were dispatched.
Source: <https://drpc.org/docs/pricing/compute-units>.

No second independent provider, historical Foundry replay, publisher evidence,
or independent reviewer annotations were completed. Existing cohort acceptance
is unchanged. Provider-family and cohort-scale claims remain pending.

## Reproduce without remote RPC

From the inner project directory in PowerShell, after placing verified binaries
in `build/tools`:

```powershell
$env:SOLC_BINARY = Join-Path $PWD 'build\tools\solc.exe'
$env:ANVIL_BINARY = Join-Path $PWD 'build\tools\anvil.exe'
$env:CAST_BINARY = Join-Path $PWD 'build\tools\cast.exe'
python scripts/replay_evm_fixtures.py --output build/local_evm_fixture_trace.json
python scripts/reproduce_paper.py
```

Compiled integration tests skip explicitly when tools are absent. Claim 26 is
marked `VERIFIED-COMPILED-EVM` only when its real integration tests pass; a skip
does not count as verification. This status does not certify historical replay.

The final reproduction run passed 328 tests, including all 201 unchanged original
tests and six real compiled integration cases. No tests were skipped in that run.
