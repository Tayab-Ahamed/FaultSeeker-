# New measurement on the original FaultSeeker benchmark

This is not a paper edit. It records a new measurement using the 115 ground-
truth files imported from `kairanskrr/FaultSeeker` at commit
`72753bd833554449efa8499f0d1775a97fb5c696` under the frozen protocol
`benchmark/protocols/original_benchmark_function_localization_v1.md`.

## Deterministic LLM-free FunctionRanker run

Command:

```bash
env -u OPENAI_API_KEY -u GOOGLE_API_KEY -u GEMINI_API_KEY \
  -u ANTHROPIC_API_KEY -u XAI_API_KEY -u GROQ_API_KEY \
  -u NVIDIA_API_KEY -u BYNARA_API_KEY -u MINIMAX_API_KEY -u ATRIA_API_KEY \
  PYTHON_DOTENV_DISABLED=true PYTHONPATH=. \
  python -u benchmark/original_benchmark_eval.py \
    --variant llm-free --model llm-free-function-ranker \
    --run-id original-v1-seed20261017 --per-tx-timeout 30
```

Observed terminal summary:

```text
variant=llm-free
n_total=115
n_ok=2
n_failed=113
recall_at_1=0.000000
recall_at_3=0.000000
recall_at_5=0.000000
actual_cost_usd=0.000000
```

The raw result for every transaction is under:

`reports/original_benchmark/llm-free/original-v1-seed20261017/raw/`

The complete manifest is:

`reports/original_benchmark/llm-free/original-v1-seed20261017/manifest.json`

## API-backed run status

No LLM-backed measurement was dispatched. The deterministic stage could not
obtain a usable historical trace for 113/115 cases. The two successful stage-1
cases were not sent through the full model-backed function-analysis path. The
API status is recorded in
`reports/original_benchmark/llm-free/original-v1-seed20261017/api_run_status.json`.
Therefore there are no provider model names, token counts, or API costs to
report, and no API result is claimed.

The implementation-paper cost claim remains unchanged: 35% modeled, not
measured. This new benchmark measurement does not support the paper's reported
Table II values because the runtime trace/source prerequisite failed for nearly
the entire imported benchmark.

## Opt-in safeguards

`reports/original_benchmark/llm-free/original-v1-seed20261017/ablations.json`
records three reporting safeguards on the same 115 rows:

1. evaluation partition guard;
2. digest-bound evidence provenance ledger;
3. trace-capability eligibility gate.

All preserve the prediction denominator and reject failed/incomplete evidence;
none changes a prediction or tunes a threshold.
