# Repository Guidelines

## Project Overview

**FaultSeeker++** is a research prototype extending the FaultSeeker baseline for AI-powered blockchain transaction fault localization. It processes on-chain exploit transactions through a multi-stage pipeline, using LLMs to identify vulnerable smart contract functions.

## Project Structure & Module Organization

The pipeline has **3 core stages**, each in its own subpackage:

```
faultseeker/
├── data_collection/      # Stage 0 — Trace collection
│   ├── txn_replayer.py   # Foundry cast run + CHAIN_RPC_MAP (8 EVM chains)
│   └── contract_downloader.py
├── forensics/            # Stage 1 — Fund flow + call sequence analysis
│   └── orchestrator.py   # Returns (txn_seq, txn_info, forensics_result)
├── function_analysis/    # Stage 2 — LLM-driven fault localization
│   ├── function_analyzer.py   # Main multi-agent loop (up to 30 iterations)
│   └── function_ranker.py
├── core/
│   ├── llm_router.py         # HybridLLMRouter — 3-tier local/cloud routing
│   └── cross_chain_runner.py # Gap 6 — multi-chain benchmarking
├── prompts/
│   ├── function_analysis/    # All LLM system & user prompts as dataclasses
│   └── forensics/
└── utils/
    └── agent.py   # OllmaAgent / GPTAgent — JSON retry + extraction logic
```

**Non-obvious wiring:** `main.py` → `orchestrator.py` → `function_analyzer.py`. The orchestrator must return `(txn_seq, txn_info, forensics_result)` as a 3-tuple; returning `None` crashes unpacking downstream.

**LLM routing:** `build_routed_agent()` in `llm_router.py` is the drop-in replacement for `build_agent()`. Pass a `HybridLLMRouter` instance to enable cost-tracked local/cloud routing.

## Build, Test, and Development Commands

```bash
# Install (editable)
pip install -e .

# Run pipeline on a single transaction
python -m faultseeker --txn <TX_HASH> --chain eth

# Run with hybrid routing (local Ollama + cloud)
python -m faultseeker --txn <TX_HASH> --chain eth --local-model phi3:mini --model gpt-4o-mini

# Batch auto-run (Windows)
.\run_faultseeker_auto.bat

# Benchmarking eval (quick test)
python run_benchmark_eval.py --limit 5 --chains eth bsc arbitrum

# Cross-chain analysis (Gap 6)
python -m faultseeker.core.cross_chain_runner --limit 5 --chains eth bsc

# Generate dataset charts
python generate_charts.py

# Validate benchmark dataset
cd benchmark && python validate_dataset.py
```

Requires `Foundry` (`cast`) in `PATH` or `foundry_bin/`. Set RPC URLs via `.env`:
```
ETHERSCAN_API_KEY=...
ETH_RPC_URL=https://rpc.ankr.com/eth
BSC_RPC_URL=https://rpc.ankr.com/bsc
OPENAI_API_KEY=...
```

## Coding Style & Naming Conventions

- **Python 3.10+**; type hints on all public methods.
- Agent classes inherit from `AbstractAgent` — override only `_send_message()`.
- Prompt strings live in `dataclass`-decorated classes under `faultseeker/prompts/`; never inline prompts in logic files.
- All JSON parsing goes through `agent._extract_json()` — do **not** use bare `eval()` or `json.loads()` directly on LLM output.
- Chain identifiers are lowercase strings: `"eth"`, `"bsc"`, `"arbitrum"`, `"optimism"`, `"base"`, `"polygon"`, `"avalanche"`, `"zksync"`.
- Cache files are written with `encoding="utf-8"` (required on Windows to avoid `UnicodeEncodeError` on trace data).

## Benchmark Dataset

`benchmark/benchmark_classification_fixed.csv` — 246 verified exploit transactions, 8 chains, 2021–2026.
Run `python benchmark/validate_dataset.py` before committing new entries.
Schema: `txn_hash, chain, num_func_calls, num_suspicious_funcs, num_address, loss_usd, class, vuln_type, reference, swc_id, dasp_category, notes`
