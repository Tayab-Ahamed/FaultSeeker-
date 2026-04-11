# FaultSeeker++

<p align="center">
  <img src="diagram1.png" alt="FaultSeeker++ Architecture" width="900">
</p>

<p align="center">
  <strong>AI-Powered Blockchain Transaction Forensics & Vulnerability Localization</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-2ea043?style=flat-square">
  <img alt="Dataset" src="https://img.shields.io/badge/dataset-246%20exploits-cb2431?style=flat-square">
  <img alt="Chains" src="https://img.shields.io/badge/chains-10%20EVM%20networks-6f42c1?style=flat-square">
  <img alt="Tests" src="https://img.shields.io/badge/tests-111%20passing-brightgreen?style=flat-square">
  <img alt="Status" src="https://img.shields.io/badge/status-research%20prototype-0969da?style=flat-square">
</p>

---

FaultSeeker++ replays exploit transactions, reconstructs execution traces, extracts deterministic security signals, ranks suspicious functions, and generates benchmark-ready forensic outputs — all in one pipeline.

Built for security researchers, auditors, and academics working on smart contract vulnerability analysis.

## What Makes This Different

Most exploit analysis tools stop at detection. FaultSeeker++ goes further:

- **Dual-path data collection** — HTML scraping with automatic JSON-RPC fallback when block explorers are WAF-protected. No chain gets left behind.
- **Hybrid model routing** — simple tasks stay on local models, heavy reasoning escalates to cloud providers. You control API spend.
- **Human-in-the-loop checkpoints** — the analyst stays in the loop at critical decision points instead of blindly trusting model output.
- **Structured evidence** — every finding comes with signal breakdowns, confidence scores, and priority rankings. Not just a boolean "vulnerable."
- **10-chain coverage** — Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche, Base, Fantom, Gnosis, and zkSync. All validated and tested.
- **Reproducible benchmarks** — 246 real exploit transactions with ground truth labels, evaluation harnesses, and CSV export.

## Pipeline Output

FaultSeeker++ emits structured forensic data at the transaction level:

```json
{
    "reentrancy": {
        "score": 0.675,
        "detected": true,
        "tier": "POSSIBLE_REENTRANCY",
        "signals": {
            "cross_function_reentry": true,
            "reentry_before_return": true,
            "state_slot_reentry": false
        }
    },
    "priority": {
        "total": 0.8754,
        "exploitability": 0.75,
        "reentrancy": 0.459,
        "flashloan": 0.0,
        "price_manipulation": 0.0,
        "liquidity_drain": 0.081,
        "reentrancy_source": "fallback"
    }
}
```

Useful for analyst triage, benchmark scoring, dataset generation, ranking experiments, and downstream model training.

## Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Transaction Hash + Chain                  │
  └──────────────────────────┬──────────────────────────────────┘
                             │
  ┌──────────────────────────▼──────────────────────────────────┐
  │           DATA COLLECTION                                    │
  │   Replay · Trace parsing · Chain metadata · Contract source  │
  │   HTML scraper → RPC fallback (dual-path)                    │
  └──────────────────────────┬──────────────────────────────────┘
                             │
  ┌──────────────────────────▼──────────────────────────────────┐
  │           FORENSICS ENGINE                                   │
  │   Signal extraction · Classification · Reentrancy analysis   │
  │   Storage-backed slot mutation · Proxy-safe delegatecall     │
  └──────────────────────────┬──────────────────────────────────┘
                             │
  ┌──────────────────────────▼──────────────────────────────────┐
  │           FUNCTION ANALYSIS                                  │
  │   Priority scoring · Function ranking · LLM investigation    │
  │   Evidence cards · Confidence scoring                        │
  └──────────────────────────┬──────────────────────────────────┘
                             │
             ┌───────────────┴───────────────┐
             │                               │
  ┌──────────▼──────────┐    ┌───────────────▼───────────────┐
  │   Forensic Report   │    │   Benchmark CSV + Charts      │
  │   Evidence Cards     │    │   Evaluation Reports          │
  └─────────────────────┘    └───────────────────────────────┘
```

## Supported Networks

| Chain | Explorer | Data Source | Status |
|-------|----------|-------------|--------|
| Ethereum | etherscan.io | HTML + RPC | ✅ |
| BSC | bscscan.com | HTML | ✅ |
| Polygon | polygonscan.com | HTML + RPC | ✅ |
| Arbitrum | arbiscan.io | HTML | ✅ |
| Optimism | optimistic.etherscan.io | HTML | ✅ |
| Avalanche | snowtrace.io | RPC fallback | ✅ |
| Base | basescan.org | HTML | ✅ |
| Fantom | ftmscan.com | RPC fallback | ✅ |
| Gnosis | gnosisscan.io | RPC fallback | ✅ |
| zkSync Era | explorer.zksync.io | RPC fallback | ✅ |

The dual-path architecture ensures every chain works reliably. When a block explorer blocks automated requests (Cloudflare WAF), the system falls back to direct JSON-RPC calls using `eth_getTransactionByHash`, `eth_getTransactionReceipt`, and `eth_getCode`.

## Repository Layout

```
faultseeker/
  core/                 pipeline orchestration, routing, confidence scoring
  data_collection/      replay, trace parsing, transaction metadata, contract download
  forensics/            signal extraction, classification, forensic result schemas
  function_analysis/    function ranking and multi-agent investigation
  prompts/              model prompts and task templates
  utils/                RPC, explorer, parser, and agent utilities

benchmark/              benchmark CSV, validation, signal evaluation harness
tests/                  111 regression and integration tests
paper/                  implementation paper skeleton
reports/                generated evaluation outputs
data/output/            single-run analysis artifacts
```

## Getting Started

### Requirements

- Python 3.10+
- Foundry `cast` on PATH (for the most reliable replay path)
- At least one cloud LLM API key for full analysis flows
- Trace-capable archive RPC access for production-quality replay

### Install

```bash
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Fill in what you need. Minimum: one LLM key + one trace-capable RPC for the target chain.

```env
# LLM providers (at least one required)
OPENAI_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=

# Explorer APIs (optional, for verified source download)
ETHERSCAN_API_KEY=
BSCSCAN_API_KEY=

# Trace-capable RPCs
ETH_RPC_URL=
BSC_RPC_URL=
```

> `debug_traceTransaction` is not available on most free RPC endpoints. For Ethereum, Tenderly provides the most reliable trace access. Foundry replay works when RPC trace methods are restricted.

### Analyze a Transaction

```bash
# Basic analysis
python -m faultseeker -txn_hash 0xYOUR_TX_HASH -chain eth

# With explainability output
python -m faultseeker -txn_hash 0xYOUR_TX_HASH -chain eth --explain

# Using a block explorer link directly
python -m faultseeker -txn_link https://etherscan.io/tx/0xYOUR_TX_HASH
```

## Benchmark & Evaluation

### Dataset

246 real exploit transactions across 10 EVM chains (2021–2026), with 80+ vulnerability labels sourced from postmortems, incident writeups, and exploit repositories.

```bash
# Validate the benchmark dataset
python benchmark/validate_dataset.py
```

### End-to-End Evaluation

```bash
python run_benchmark_eval.py --limit 5
python run_benchmark_eval.py --chains eth arbitrum base --limit 10
python run_benchmark_eval.py --full
```

Results land in `reports/eval/` as JSON, CSV, and summary text files.

### Signal-Focused Evaluation

```bash
python benchmark/run_eval.py --chain eth --limit 20 --save
python benchmark/run_eval.py --signals-only --limit 50
```

## Reentrancy Engine

The reentrancy detector goes beyond simple repeated-address checks:

- **Storage-backed detection** — tracks SSTORE operations per contract, flags write-after-external-call patterns
- **Fallback mode** — structural analysis when storage traces are unavailable (public RPCs)
- **Proxy-safe** — normalizes delegatecall chains before analysis
- **Cross-function support** — detects reentry across different function selectors
- **Tiered output** — `CONFIRMED`, `POSSIBLE_REENTRANCY`, `WEAK_SIGNAL`, `NONE` with explainable signals

## Model Providers

Hybrid routing: simple tasks stay local, heavy reasoning escalates to cloud.

| Provider | Use Case |
|----------|----------|
| Ollama (local) | Quick classification, low-stakes analysis |
| OpenAI | Deep function investigation, complex reasoning |
| Google Gemini | Alternative cloud path |
| Anthropic | Function analysis, code review |
| Alibaba Qwen (DashScope) | Alternative cloud path |
| xAI Grok | Alternative cloud path |

## Development

```bash
# Full test suite (111 tests)
python -m pytest tests -q

# Specific test modules
python -m pytest tests/test_reentrancy_state_signals.py -q
python -m pytest tests/test_agent_security.py -q
python -m pytest tests/test_pipeline_parse.py -q

# Multi-chain data collection validation
python test_chains.py
```

## Cross-Chain Analysis

```bash
python -m faultseeker.core.cross_chain_runner --limit 5 --chains eth bsc arbitrum
```

## Charts

```bash
python generate_charts.py
```

## Citation

```bibtex
@article{faultseekerpp2026,
  title   = {FaultSeeker++: Enhancing AI-Powered Blockchain Transaction Fault Localization},
  author  = {[Authors]},
  journal = {[Venue]},
  year    = {2026}
}
```

## License

Released under the [MIT License](LICENSE).
