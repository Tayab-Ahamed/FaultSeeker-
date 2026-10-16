# FaultSeeker++ local demo

The live demo is intentionally no-LLM. It runs deterministic Stage 1 only,
uses public/free explorer and RPC fallbacks, and never constructs or calls an
LLM provider. The default pipeline behavior is unchanged.

## Clean setup

The supported runtime is **Python 3.11.9** (`.python-version`). From a fresh
checkout, run these commands from the repository root:

```bash
python --version
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The requirements file includes the local test and demo dependencies used by
the rehearsal: `pytest`, `networkx`, `ollama`, `matplotlib`, `eth-utils`,
`openai`, `pandas`, `eth-hash[pycryptodome]`, `rlp`, and `eth-account`. The
same `requirements.txt` is used by `Dockerfile.benchmark`; no global install
or paid provider is required. On Windows PowerShell, use
`.venv\Scripts\python.exe` in place of `.venv/bin/python`; the commands below
use the POSIX/Git-Bash form.

## Run on an accepted-cohort transaction

From the repository root:

```bash
env -u DRPC_RPC_URL -u DRPC_API_KEY \
  -u ETH_RPC_URL -u BSC_RPC_URL -u BASE_RPC_URL \
  -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u GOOGLE_API_KEY \
  -u XAI_API_KEY -u DASHSCOPE_API_KEY \
  PYTHON_DOTENV_DISABLED=true \
  PYTHONPATH=. .venv/bin/python -m faultseeker.main \
    --no-llm \
    -txn_hash 0x0788ba222970c7c68a738b0e08fb197e669e61f9b226ceec4cab9b85abe8cceb \
    -chain eth \
    -output demo_outputs/eth_0x0788ba22.json
```

Clean-clone prerequisite: `.venv/` is intentionally not committed. The
command therefore requires the project environment to have been provisioned
before rehearsal; it is not a hidden runtime step performed by the demo.
Without `.venv/bin/python`, the exact command fails before application code
starts.

Use another accepted-cohort row if needed:

```bash
PYTHONPATH=. .venv/bin/python -m faultseeker.main --no-llm \
  -txn_hash 0x8fcdfcded45100437ff94801090355f2f689941dca75de9a702e01670f361c04 \
  -chain base -output demo_outputs/base_0x8fcdfcd.json

PYTHONPATH=. .venv/bin/python -m faultseeker.main --no-llm \
  -txn_hash 0x13d19809b19ac512da6d110764caee75e2157ea62cb70937c8d9471afcb061bf \
  -chain bsc -output demo_outputs/bsc_0x13d19809.json
```

The accepted-cohort source is `benchmark/benchmark_classification_fixed.csv`.
The command writes one JSON file per successful run. Each result includes
`analysis_mode=no-llm-free-rpc`, `stage_completed=stage1`,
`stage2_bypassed=true`, `llm_cost=0.0`, and the observed trace coverage.

## Expected output

The terminal output should include:

```text
No-LLM mode: running real deterministic Stage 1 via free/public RPC
Results saved to: demo_outputs/<name>.json
Stage 2 skipped; no model/provider call was made
```

The verdict and signals depend on the transaction and on what the public RPC
returns. This demo does not claim function localization or Stage 3 calibrated
scores.

## Free-RPC expectations and fallback

The repository provides public fallbacks for Ethereum, BSC, Base, Polygon,
Arbitrum, Optimism, Avalanche, Fantom, Gnosis, and zkSync in
`faultseeker/utils/rpc_provider.py`. Public nodes may support receipt reads but
not archive tracing. A transaction can therefore fail because the provider is
pruned, rate-limited, or does not support `debug_traceTransaction`.

If a live run fails, keep the failure log and show the corresponding saved JSON
from `demo_outputs/` instead. Say explicitly that the saved output is a prior
local Stage-1 capture and that the current network call was unavailable. Do
not present a saved output as a fresh live replay.
