# Historical opcode capture through Anvil

## Result: one verified replay capture; comparison timed out

Selected from `benchmark/benchmark_classification_fixed.csv`:

| Transaction | Selection label | Outcome |
| --- | --- | --- |
| `0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6` | labeled reentrant in benchmark_classification_fixed.csv | Captured and validated |
| `0x90b468608fbcc7faef46502b198471311baca3baab49242a4a85b73d4924379b` | not labeled reentrant in benchmark_classification_fixed.csv | Timed out; no accepted capture |

The CSV contains no benign-labeled rows. The second transaction is **not** a
benign control. No independent incident-label adjudication is asserted.

The successful capture has **21,300 opcode steps, 80 SLOADs and 29 SSTOREs**.
It forks Ethereum at block 16,288,199 and mines the first seven signed
transactions of block 16,288,200 in canonical order, including the target at
index 6. No sender impersonation or nonce, balance, storage, code or gas-check
overrides are used. Signature envelopes are reconstructed from canonical block
fields and every resulting Keccak transaction hash must match.

The replay matches the historical target receipt's status, gas used, transaction
index, contract address and emitted logs. Block number, timestamp, base fee,
coinbase, gas limit and prevRandao are checked against the original environment.
Both callTracer and full structLogs are captured from **local Anvil**, not dRPC.
Normalization is complete; SLOAD/SSTORE counts match raw opcodes and every
event's storage owner matches its call frame, including delegatecall ownership.

The compressed artifact contains the canonical block/transaction/receipt,
replayed receipt and prefix hashes, both raw traces, and normalized storage
events. `final_accounting.json` records its SHA-256 digest. The test
`test_recorded_historical_capture_validates_storage_and_receipt` independently
recomputes signed envelopes, receipt equivalence and normalization offline.

## Failure boundary and stop

The initial attempt stopped before forking because dRPC returned HTTP 400 for
`eth_getRawTransactionByHash` (five requests). Reconstructing and hash-checking
the original signed envelopes removed that dependency.

The next attempt captured the first transaction, then the comparison failed
with `TimeoutError: timed out` at the runner's 120-second local RPC boundary.
That attempt made 413 upstream requests in total. Four proxy requests also
received local `ValueError` rejections. The original run did not record the
last local method or rejected method names, so the artifact does **not** establish
whether submission, mining or tracing caused the timeout, or identify its
underlying cause. A client disconnect occurred when an upstream response
outlasted the Anvil-side request. The runner now includes the local method in
future timeout errors and handles such disconnects without a traceback.

As requested, **no further live attempts were made after this failure**. The
comparison has no accepted trace. No archive-data, provider-capability, or EVM
failure is inferred from a timeout alone.

## Budget and tests

- This task: **418 dispatched upstream RPC requests**, including failures;
  estimated **$0.002508** at $6 per million requests.
- Including the seven earlier probes: **425 requests**, estimated **$0.002550**.
- These are conservative request-based estimates, not confirmed billing.
- All upstream traffic, including Anvil's lazy archive reads, passes through a
  loopback read-only proxy. Every attempt reserves budget in the same durable
  ledger used by model calls. Prior probes are imported once as an explicit
  estimate. The per-run request limit and cumulative $10 cap stop dispatch.
- Price source: <https://drpc.org/docs/pricing/compute-units>.
- Full suite: **336 passed, 1 skipped**, with local compiled fixtures enabled.
  The skip is the opt-in live historical test; recorded-capture validation ran.
  All 201 original test sources remain unchanged.

## Claim scope

Claim 26 advances from `VERIFIED-COMPILED-EVM` to
`VERIFIED-HISTORICAL-ETHEREUM-SAMPLE`, contingent on passing recorded-capture
validation as well as its compiled acceptance tests. Evidence pointers are in
the claim registry. This proves extraction on **one historical Ethereum
transaction**, not a complete two-case experiment or all-chain replay.

Claim 25 remains pending for broader live RPC capability. Cohort and empirical
claims remain `BLOCKED-BY-DATA`; no independent publisher/reviewer manifest or
newly accepted cohort row was produced. The paper is unchanged.

## Running later

From the inner project directory, with `.env` configured:

```powershell
python scripts/replay_historical_opcodes.py --execute-live --max-requests 5000
```

The default batch is the two transactions above. Use `--transaction HASH` to
select a specific Ethereum row. Without `--execute-live`, no requests are made.
The raw upstream URL is never passed to Anvil; its `--fork-url` is a loopback
metered proxy. Anvil's disk RPC cache is disabled. The supplied Anvil binary
must support steps tracing, next-block environment overrides and FIFO mining.

Live integration test (dispatches counted requests, so keep it explicitly opt-in):

```powershell
$env:FAULTSEEKER_RUN_HISTORICAL_REPLAY = '1'
python -m pytest tests/test_historical_fork_replay.py -q
```

It skips when `DRPC_RPC_URL` is unset or live execution is not opted in. When
enabled, it uses the real shared spend ledger instead of the simulated-usage
ledger used by other tests.
