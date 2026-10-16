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
