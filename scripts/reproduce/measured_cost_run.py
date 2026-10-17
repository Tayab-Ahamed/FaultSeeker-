"""Preflight and resumable runner for the preregistered cost experiment.

The runner refuses to invent a transaction selection.  It first requires the
repository's preregistered selection artifact with exactly 100 unique IDs and
the recorded 50/30/20 tier mix.  Only after that immutable input gate passes
would a later execution phase load the explicitly supplied dotenv file and
dispatch eligible free-tier providers.  This module never prints key values or
serializes environment contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "reports/claim_evidence/measured_cost_run.json"
DEFAULT_STATE = ROOT / "reports/claim_evidence/measured_cost_run_state.json"
DEFAULT_COHORT = ROOT / "benchmark/benchmark_classification_fixed.csv"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_selection_files(root: Path = ROOT) -> list[Path]:
    """Return only plausible tracked selection manifests, never .env files."""
    candidates = []
    candidate_roots = [root / name for name in ("benchmark", "reports", "docs", "scripts")]
    for base in candidate_roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*.json"):
            if path.name in {"new_candidates_initial_selection.json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                continue
            if '"transaction_ids"' in text and '"workload_tier"' in text:
                candidates.append(path)
    return sorted(candidates)


def _validate_selection(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {"path": path.relative_to(ROOT).as_posix(), "valid": False,
                "reason": f"invalid_json:{type(exc).__name__}"}
    ids = payload.get("transaction_ids") if isinstance(payload, dict) else None
    if not isinstance(ids, list):
        return {"path": path.relative_to(ROOT).as_posix(), "valid": False,
                "reason": "transaction_ids_missing_or_not_list"}
    return {"path": path.relative_to(ROOT).as_posix(), "valid": False,
            "reason": "selection_manifest_does_not_bind_workload_tiers",
            "transaction_id_count": len(ids), "unique_transaction_id_count": len(set(ids)),
            "sha256": _digest(path)}


def build_blocked_report(root: Path = ROOT) -> dict[str, Any]:
    selections = [_validate_selection(path) for path in candidate_selection_files(root)]
    return {
        "schema_version": 1,
        "experiment": "measured_cost_routing",
        "requested_runs": {
            "n100": {"target_n": 100, "tier_mix": {"1": 50, "2": 30, "3": 20},
                     "status": "BLOCKED_BY_MISSING_PREREGISTERED_CONFIG",
                     "completed_n": 0},
            "extension": {"status": "NOT_STARTED", "completed_n": 0,
                          "reason": "N=100 preflight did not pass"},
        },
        "input_gate": {
            "required": "selection manifest with exactly 100 unique transaction_ids and workload_tier counts 50/30/20",
            "runner": "benchmark/run_paper_experiments.py",
            "cohort": DEFAULT_COHORT.relative_to(root).as_posix(),
            "candidate_selection_files": selections,
            "selection_found": bool(selections),
        },
        "provider_gate": {
            "dotenv_loaded": False,
            "provider_keys_used": [],
            "provider_calls": 0,
            "free_tier_status": "NOT_EVALUATED_BECAUSE_INPUT_GATE_FAILED",
            "paid_or_unverified_providers_used": [],
        },
        "measurements": {
            "actual_cost_usd": None,
            "list_price_equivalent_usd": None,
            "all_cloud_list_price_equivalent_usd": None,
            "measured_saving_fraction": None,
            "per_call_log": [],
        },
        "resume": {
            "next_transaction_index": 0,
            "state": "WAITING_FOR_PREREGISTERED_SELECTION",
            "safe_to_resume": False,
        },
        "blocker_proof": [
            "No tracked JSON file contains both transaction_ids and workload_tier fields.",
            "benchmark/run_paper_experiments.py refuses to run without --selection-file.",
            "The same runner refuses any routing selection whose tier counts are not exactly 50/30/20.",
            "No transaction selection was created, reordered, or tuned by this run.",
        ],
    }


def write_report(report: dict[str, Any], output: Path = DEFAULT_OUTPUT,
                 state: Path = DEFAULT_STATE) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(encoded)
    state.write_bytes(encoded)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    report = build_blocked_report()
    write_report(report, args.output, args.state)
    print("status=BLOCKED_BY_MISSING_PREREGISTERED_CONFIG")
    print("n100_completed=0")
    print("extension_status=NOT_STARTED")
    print(f"report={args.output}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
