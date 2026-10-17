# Original FaultSeeker benchmark measurements

This directory contains new measurements on the imported original FaultSeeker
ASE 2025 benchmark. The input attribution and frozen protocol are documented
in:

- `benchmark/original_faultseeker/ATTRIBUTION.md`
- `benchmark/protocols/original_benchmark_function_localization_v1.md`

The completed deterministic run is:

```text
reports/original_benchmark/llm-free/original-v1-seed20261017/
```

It contains one raw JSON result for each of the 115 benchmark transactions,
the aggregate manifest, and resumable state. Failures remain in the denominator
as zero. The run used no LLM provider and no API key.

## Exact result

```text
n_total=115
n_ok=2
n_failed=113
Recall@1=0.000000
Recall@3=0.000000
Recall@5=0.000000
actual_cost_usd=0.000000
```

The two successful deterministic trace paths did not hit their function-level
ground-truth targets. The 113 failures were retained, primarily because
configured public RPC paths did not provide a usable historical trace; 13
reached the bounded per-transaction timeout.

The three opt-in evidence safeguards are reported in `ablations.json`:

- evaluation partition guard;
- digest-bound evidence provenance;
- trace-capability eligibility gate.

These safeguards preserve the prediction outputs and do not turn failed or
synthetic inputs into empirical successes.

The API-backed status is recorded separately in
`llm-free/original-v1-seed20261017/api_run_status.json`. No provider was
dispatched: the model keys were not verified as free-tier eligible, and 113
cases lacked a usable trace/source prerequisite for model analysis.
