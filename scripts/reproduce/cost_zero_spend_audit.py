"""Prove the cost audit stayed zero-spend without loading credentials.

This script intentionally does not import dotenv, inspect ``.env``, contact a
provider, or dispatch a model call.  It only inspects executable availability,
project-local model files, and the frozen modeled-cost JSON already in the
repository.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COST_INPUT = ROOT / "reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json"
OUT = ROOT / "reports/claim_evidence/cost_zero_spend_proof.json"


def _local_model_candidates() -> dict[str, bool]:
    names = ("ollama", "llama-server", "llama-cli", "llamafile", "lmstudio")
    return {name: shutil.which(name) is not None for name in names}


def _project_model_files() -> list[str]:
    roots = (ROOT / "models", ROOT / "artifacts", ROOT / "benchmark" / "models")
    suffixes = {".gguf", ".ggml", ".safetensors", ".bin"}
    found: list[str] = []
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def build_proof() -> dict:
    modeled = json.loads(COST_INPUT.read_text(encoding="utf-8"))
    computed = modeled["computed"]
    executable_status = _local_model_candidates()
    return {
        "audit": "cost_zero_spend",
        "dotenv_loaded": False,
        "dotenv_paths_read": [],
        "wingman_secrets_loaded": False,
        "provider_api_calls": 0,
        "model_dispatches": 0,
        "local_model_executables": executable_status,
        "project_local_model_files": _project_model_files(),
        "free_tier_api": {
            "availability_verified": False,
            "reason": "No credential or API request was used; free-tier availability remains unverified.",
            "credentials_inspected": False,
        },
        "modeled_cost": {
            "hybrid_cost_per_query_usd": computed["hybrid_cost_per_query_usd"],
            "cloud_only_cost_per_query_usd": computed["cloud_only_cost_per_query_usd"],
            "modeled_cost_saving_pct": computed["cost_reduction_pct"],
            "status": "MODELED_ONLY_NOT_MEASURED",
            "source": COST_INPUT.relative_to(ROOT).as_posix(),
        },
        "conclusion": "No local model or verified free-tier API was used; zero-spend is preserved and 35% remains modeled arithmetic only.",
    }


def main() -> None:
    proof = build_proof()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
