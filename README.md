<div align="center">

<img src="diagram1.png" alt="FaultSeeker++ Banner" width="800"/>

# 🔍 FaultSeeker++

### _AI-Powered Blockchain Transaction Fault Localization_

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Dataset](https://img.shields.io/badge/Dataset-246%20Exploits-red?style=for-the-badge&logo=databricks&logoColor=white)]()
[![Chains](https://img.shields.io/badge/Chains-8%20EVM-purple?style=for-the-badge&logo=ethereum&logoColor=white)]()
[![LLM](https://img.shields.io/badge/LLM-Hybrid%20Routing-orange?style=for-the-badge&logo=openai&logoColor=white)]()
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-blue?style=for-the-badge)]()

**FaultSeeker++** is an enhanced, AI-powered framework for automated smart contract vulnerability localization. It analyzes on-chain exploit transactions and pinpoints the exact functions responsible — across 8 EVM-compatible blockchains.

[📖 Paper](#-research) · [🚀 Quick Start](#-quick-start) · [📊 Dataset](#-benchmark-dataset) · [🏗️ Architecture](#-architecture) · [🤖 Models](#-supported-llm-providers)

</div>

---

## ✨ What Makes FaultSeeker++ Different

> The original [FaultSeeker](https://github.com/) baseline was limited to Ethereum, required cloud-only LLMs, and had a small benchmark. FaultSeeker++ addresses **7 research gaps** with production-grade enhancements.

| Gap                             | Enhancement                              | Impact                             |
| ------------------------------- | ---------------------------------------- | ---------------------------------- |
| ☁️ **Cloud Dependency**         | Hybrid LLM routing (local ↔ cloud)       | Up to 70% API cost reduction       |
| 👤 **Black-box Analysis**       | Human-in-the-Loop analyst checkpoints    | Expert-guided investigation        |
| 🔍 **No Explainability**        | Structured evidence cards per finding    | Auditable, reproducible results    |
| 📊 **No Confidence Scoring**    | Per-function confidence scores (0–1)     | Ranked vulnerability output        |
| 🔗 **Single Chain**             | Archive-capable RPC for 8 EVM chains     | Full DeFi ecosystem coverage       |
| 📈 **No Cross-Chain Analytics** | Cross-chain forensic benchmarking runner | Comparative analysis across chains |
| 📁 **Small Dataset**            | 246 verified exploits, 2021–2026         | 2× baseline benchmark size         |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`cast` in PATH)
- At least **one** LLM provider (see [Supported Models](#-supported-llm-providers))

### Installation

```bash
# 1. Clone
git clone https://github.com/yourusername/FaultSeeker-plus-plus.git
cd FaultSeeker-plus-plus

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# → Edit .env and add your preferred API key (only ONE needed)
```

### Analyze a Transaction

```bash
# Auto-detects the best available LLM from your .env
python -m faultseeker -txn_hash 0x56e09abb35ff246e370cc0b5b0f9b620b... -chain eth

# With explainability (shows evidence cards + confidence scores)
python -m faultseeker -txn_hash 0x... -chain bsc --explain

# Full automation (Windows)
.\run_faultseeker_auto.bat
```

> **No `--model` flag needed.** FaultSeeker++ auto-detects which API keys you have and selects the best model automatically.

---

## 🤖 Supported LLM Providers

FaultSeeker++ supports **5 cloud providers** out of the box — just set the corresponding key in `.env`:

| Provider              | Models                                 | Env Variable        | Cost                |
| --------------------- | -------------------------------------- | ------------------- | ------------------- |
| 🟢 **Ollama** (Local) | phi3:mini, qwen2, tinyllama, llama3:8b | _(none)_            | **Free**            |
| 🔴 **Alibaba Qwen**   | qwen-turbo, qwen-plus, qwen-max        | `DASHSCOPE_API_KEY` | ~$0.02/1M tokens    |
| 🔵 **Google Gemini**  | gemini-2.0-flash, gemini-1.5-pro       | `GOOGLE_API_KEY`    | Free tier available |
| ⚫ **xAI Grok**       | grok-3-mini, grok-3                    | `XAI_API_KEY`       | ~$0.30/1M tokens    |
| 🟡 **OpenAI**         | gpt-4o-mini, gpt-4.1                   | `OPENAI_API_KEY`    | ~$0.15/1M tokens    |
| 🟠 **Anthropic**      | claude-3-haiku                         | `ANTHROPIC_API_KEY` | ~$0.25/1M tokens    |

**Hybrid routing** automatically uses local models for simple tasks (classification, filtering) and cloud models only for complex reasoning — reducing API costs by up to 70%.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FaultSeeker++ Pipeline                     │
│                                                                 │
│  Transaction Hash + Chain                                       │
│          │                                                      │
│          ▼                                                      │
│  ┌───────────────┐    Archive RPC     ┌──────────────────────┐ │
│  │  Txn Replayer │───────────────────▶│  Execution Trace     │ │
│  │  (Foundry)    │  8 EVM Chains      │  (JSON call tree)    │ │
│  └───────────────┘                    └──────────┬───────────┘ │
│                                                  │             │
│          ┌───────────────────────────────────────┼──────────┐  │
│          ▼                                       ▼          │  │
│  ┌───────────────┐                    ┌──────────────────┐  │  │
│  │   Forensics   │                    │  Txn Sequencer   │  │  │
│  │  Orchestrator │                    │  + Info Collector│  │  │
│  │  (Fund Flow)  │                    │  (Call Patterns) │  │  │
│  └───────┬───────┘                    └────────┬─────────┘  │  │
│          │                                     │            │  │
│          └─────────────┬───────────────────────┘            │  │
│                        ▼                                    │  │
│           ┌────────────────────────┐                        │  │
│           │   Function Ranker      │                        │  │
│           │   (Suspicious Calls)   │                        │  │
│           └────────────┬───────────┘                        │  │
│                        ▼                                    │  │
│  ┌─────────────────────────────────────────────────────┐   │  │
│  │           Multi-Agent Function Analyzer              │   │  │
│  │                                                     │   │  │
│  │  HybridLLMRouter ──► Tier 1: Local (simple tasks)  │   │  │
│  │       │              Tier 2: Local + Cloud fallback │   │  │
│  │       └─────────────▶ Tier 3: Cloud (deep analysis) │   │  │
│  │                                                     │   │  │
│  │  ┌──────────┐  ┌────────────┐  ┌────────────────┐  │   │  │
│  │  │ Reasoning│  │ Generation │  │   Processing   │  │   │  │
│  │  │  Agent   │  │   Agent    │  │     Agent      │  │   │  │
│  │  └──────────┘  └────────────┘  └────────────────┘  │   │  │
│  │                                                     │   │  │
│  │  HITL Checkpoints ──► Analyst Input (Gap 2)        │   │  │
│  └─────────────────────────────────────────────────────┘   │  │
│                        │                                    │  │
│                        ▼                                    │  │
│           ┌────────────────────────┐                        │  │
│           │   Evidence Cards       │ ◄── Gap 3 (Explain.)   │  │
│           │   Confidence Scoring   │ ◄── Gap 4 (Scoring)    │  │
│           │   Ranked Vuln. Output  │                        │  │
│           └────────────────────────┘                        │  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Benchmark Dataset

The largest publicly-validated DeFi exploit benchmark spanning **8 EVM chains** and **5 years** of real-world attacks.

```
Total Transactions : 246
Year Coverage      : 2021 – 2026
Chains             : ETH · BSC · Arbitrum · Optimism · Base · Polygon · Avalanche · zkSync
Unique Vuln Types  : 80+
Sources            : DeFiHackLabs · BlockSec · PeckShield · SlowMist · CertiK
```

### Chain Distribution

| Chain         | Entries | %     | Notable Exploits                                              |
| ------------- | ------- | ----- | ------------------------------------------------------------- |
| **Ethereum**  | 142     | 57.7% | Penpie ($27M), UwuLend ($19M), BalancerV2 ($120M), GMX ($41M) |
| **BSC**       | 33      | 13.4% | FourMeme ($183K), Pancake logic flaws, Bankroll ($234K)       |
| **Arbitrum**  | 16      | 6.5%  | Radiant Capital ($4.5M), DeltaPrime, GMX V1                   |
| **Base**      | 16      | 6.5%  | CompoundFork flash loan, oracle manipulation                  |
| **Optimism**  | 15      | 6.1%  | ResupplyFi ($9.6M), access control failures                   |
| **Polygon**   | 11      | 4.5%  | 0VIX oracle attack ($2M), GAMEE access control                |
| **Avalanche** | 8       | 3.3%  | Platypus Finance ($8.5M), DeltaPrime ($12.9K)                 |
| **zkSync**    | 5       | 2.0%  | EraLend read-only reentrancy ($3.4M), Venus ($717K)           |

### Vulnerability Distribution

| Rank | Type                        | Count |
| ---- | --------------------------- | ----- |
| 1    | Price Manipulation / Oracle | 25    |
| 2    | Business Logic Flaw         | 19    |
| 3    | Logic Flaw                  | 16    |
| 4    | Access Control              | 16    |
| 5    | Reentrancy                  | 14    |
| 6    | Flash Loan Attack           | 11    |
| 7    | Lack of Access Control      | 9     |
| 8    | Arbitrary External Call     | 8     |
| 9    | Precision Loss              | 6     |
| 10   | Incorrect Input Validation  | 5     |

### Validate the Dataset

```bash
cd benchmark
python validate_dataset.py
```

Expected output: `246 entries · 0 duplicates · 8 chains · PASSED`

---

## 📈 Evaluation & Benchmarking

### Quick Evaluation (5 transactions per chain)

```bash
python run_benchmark_eval.py --limit 5
```

### Full Benchmark

```bash
python run_benchmark_eval.py --full
```

### Cross-Chain Analysis (Gap 6)

```bash
python -m faultseeker.core.cross_chain_runner --limit 5 --chains eth bsc arbitrum
```

### Generate Publication Charts

```bash
python generate_charts.py
# → reports/charts/*.png (5 charts ready for paper)
```

All results auto-save to `reports/` as:

- `eval_results_*.json` — per-transaction breakdown
- `eval_results_*.csv` — spreadsheet format
- `eval_summary_*.txt` — **LaTeX table** ready to paste into the paper

---

## 🗂️ Project Structure

```
FaultSeeker++/
├── faultseeker/
│   ├── core/
│   │   ├── auto_model_selector.py   # Auto-detects best LLM from .env
│   │   ├── llm_router.py            # Hybrid 3-tier routing (Gap 1)
│   │   ├── cross_chain_runner.py    # Multi-chain benchmarking (Gap 6)
│   │   └── pipeline.py
│   ├── data_collection/
│   │   ├── txn_replayer.py          # Foundry cast + 8-chain RPC (Gap 5)
│   │   └── contract_downloader.py
│   ├── forensics/
│   │   └── orchestrator.py          # Fund flow + call sequence analysis
│   ├── function_analysis/
│   │   ├── function_analyzer.py     # Multi-agent LLM loop (Gaps 2,3,4)
│   │   └── function_ranker.py
│   ├── prompts/                     # All LLM prompts as versioned dataclasses
│   └── utils/
│       └── agent.py                 # OllmaAgent · GPTAgent · UniversalAgent
├── benchmark/
│   ├── benchmark_classification_fixed.csv   # 246-entry dataset
│   └── validate_dataset.py
├── paper/
│   └── FaultSeeker_Plus_Plus_Implementation.tex   # Full paper skeleton
├── run_benchmark_eval.py    # End-to-end evaluation script
├── run_faultseeker_auto.bat # Windows automation script
├── generate_charts.py       # 5 publication-ready charts
├── .env.example             # API key template
└── AGENTS.md                # Contributor guide
```

---

## 📖 Research

FaultSeeker++ addresses 7 research gaps identified in the FaultSeeker baseline:

```
Gap 1: Cloud LLM dependency    → Hybrid routing (local + cloud)
Gap 2: Black-box analysis      → Human-in-the-Loop checkpoints
Gap 3: No explainability       → Evidence cards with reasoning traces
Gap 4: No confidence scoring   → Per-function scores (0.0–1.0)
Gap 5: Single chain            → 8 EVM chains, archive-node RPCs
Gap 6: No cross-chain analysis → Comparative forensic benchmarking
Gap 7: Small dataset           → 246 exploits, 2021–2026, 8 chains
```

**Implementation Paper:** `paper/FaultSeeker_Plus_Plus_Implementation.tex`
_(Fill result tables after running `run_benchmark_eval.py` on your hardware)_

---

## 🔧 Configuration

```bash
cp .env.example .env
```

Key variables (set **at least one** cloud API key):

```env
# Cloud LLM — pick one
OPENAI_API_KEY=sk-...
DASHSCOPE_API_KEY=sk-...        # Qwen (cheapest: $0.02/1M tokens)
GOOGLE_API_KEY=AIza...           # Gemini (free tier available)
XAI_API_KEY=xai-...             # Grok

# Explorer keys (for source code download)
ETHERSCAN_API_KEY=...
BSCSCAN_API_KEY=...
```

---

## 📋 Citation

If you use FaultSeeker++ in your research, please cite:

```bibtex
@article{faultseekerpp2026,
  title   = {FaultSeeker++: Enhancing AI-Powered Blockchain Transaction
             Fault Localization via Hybrid LLM Routing, Multi-Chain
             Coverage, and an Expanded Benchmark Dataset},
  author  = {[Authors]},
  journal = {[Venue]},
  year    = {2026}
}
```

<div align="center">

Built with ❤️ for the blockchain security research community

**FaultSeeker++ — Because every exploit deserves an explanation.**

</div>
