# Nara pilot transport deadline

The production pilot retains its exact gateway endpoint and 60-second setting.
The default transport now executes a single HTTP POST in an isolated Python
worker. The worker uses the default TLS trust store, rejects redirects, and
does not retry. The parent validates the endpoint before starting the worker;
the worker independently validates it before opening a connection.

Headers and request bytes pass through stdin, never process arguments or
temporary credential files. Worker stderr is discarded. Error messages are
sanitized, and raw or JSON-escaped credential echoes are rejected. Windows
workers start without a visible window.

The monotonic deadline includes payload serialization, process startup and IPC.
An explicitly joined watchdog terminates the worker even when Windows blocks
the calling thread while writing stdin. The parent drains and reaps the worker
before reporting deadline expiry. Normal completion cancels and joins the
watchdog. Process cleanup and OS scheduling add return-time tolerance; this is
not a strict real-time guarantee. Closing the client cannot cancel or refund
an inference job already accepted by a remote provider.

The pilot records failed-attempt elapsed time and a typed deadline indicator.
Failure still conservatively settles the existing reservation when provider
usage is unavailable, then blocks all subsequent role dispatch. Injected
transports are labeled separately from the default deadline transport.

## Software validation versus research evidence

Local servers, sleeping workers and mocked failures in the transport tests are
software correctness fixtures only. They do not establish any paper metric,
localization result, provider capability or research claim. They must not be
used in the claim registry, benchmark results or paper as empirical evidence.
The existing research pilot outputs and their historical timing remain unchanged.
No new live gateway/RPC call, held-out evaluation or claim promotion accompanies
this change. The prepared inference proposal remains unapproved.

Focused developer checks:

```powershell
python -m pytest -q tests/test_nara_http_transport.py tests/test_pilot_deadline_integration.py tests/test_nara_pilot_provider.py tests/test_train_gateway_pilot.py
```

These check delayed and trickled headers/bodies, HTTP error handling, blocked
stdin, worker cleanup, endpoint/redirect restrictions, credential handling and
pilot reservation/settlement behavior. Loopback process tests require local
socket access. The complete existing test suite remains the commit gate.

## Standing TRAIN allowance

The explicit standing user approval allows Agnes 2.5 Flash without a request cap or per-batch dollar ceiling. It retains the shared $10 cumulative conservative spend cap, a durable 7M raw-token UTC-day guard, TRAIN-only public inputs and immediate stop on any error/rate limit without retries. The local UTC accounting bucket is not an attestation of the provider's reset timezone or balance. Gateway allowance enforcement remains authoritative; any rejection stops the batch.

Every request reserves twice its UTF8 payload byte count plus 1024 input-framing tokens and the 4096 output cap. Valid provider usage settles the token allocation; missing/invalid usage charges the reservation. Historic pilot usage is imported once by UTC run date. Undated old source-consensus records are conservatively carried into the current bucket once, with real usage where available and full bounds otherwise. Previously settled standing requests are reconciled by their reservation IDs instead of imported again. The separate dollar ledger still records every attempted request; a typed refusal before dispatch cancels its dollar reservation rather than booking nonexistent spend.

Standing runs use a 300-second total transport deadline because genuine earlier successful responses took up to 198.515 seconds. This permits slower single attempts; it introduces no retries. A run-specific permit and hash-bound summary report requests, complete cases, token state, conservative dollar state and the terminal reason. The historical bounded-pilot approval artifacts and results remain unchanged. Fixtures validate these controls only and provide no research results or claim promotions.

## Safe failure diagnostics

The worker sends only allowlisted exception and nested URLError-reason classes, a validated execution phase, and numeric OS/SSL verification codes. An HTTP status is recorded only if an actual response was opened. Parent decoding preserves a typed TransportWorkerError and sanitizes its metadata again at the pilot persistence boundary. Unknown fields, arbitrary class names, exception messages, URLs, headers and bodies are discarded. Crashes and malformed worker packets retain safe classifications rather than arbitrary stdout/stderr.

This fixes a diagnostic loss in the terminal real run 20261016T034806-c4ff4f0a. That historical run remains a failed one-attempt, zero-completion batch: its specific cause cannot be recovered or retroactively assigned to DNS/TLS/provider/rate limiting. The software correction makes no claim about transport availability, future completion, model quality or paper metrics. No live request is retried as part of this change.
