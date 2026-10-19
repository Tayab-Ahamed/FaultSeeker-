"""Build the machine-readable claim-closure scoreboard from retained evidence.

The ledger is deliberately conservative: the historical claim JSON files are
the source of reviewed decisions, while the repository claim registry supplies
the canonical claim title, scope, tests, and required evidence.  This command
does not run experiments, contact providers, or alter frozen research files.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUSES = {
    "VERIFIED_IMPLEMENTATION",
    "REPRODUCED_EMPIRICAL",
    "MODELED_NOT_MEASURED",
    "SIMULATED",
    "UNVERIFIED",
    "CONTRADICTED_BY_CURRENT_EVIDENCE",
    "EXTERNALLY_BLOCKED",
}

CATEGORY_BY_ID = {
    1: "reproducibility",
    2: "reproducibility",
    3: "dataset",
    4: "dataset",
    5: "dataset",
    6: "dataset",
    7: "dataset",
    8: "dataset",
    9: "implementation",
    10: "implementation",
    11: "implementation",
    12: "implementation",
    13: "empirical_performance",
    14: "empirical_performance",
    15: "case_study",
    16: "implementation",
    17: "provider_conformance",
    18: "cost",
    19: "implementation",
    20: "implementation",
    21: "cost",
    22: "localization",
    23: "calibration",
    24: "implementation",
    25: "provider_conformance",
    26: "implementation",
    27: "empirical_performance",
    28: "calibration",
    29: "human_study",
    30: "reproducibility",
    31: "reproducibility",
}


def _git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8-sig"))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _status(claim: dict[str, Any], closure: dict[str, Any]) -> str:
    # These two historical decisions cannot be promoted from the retained
    # closure snapshots in this working tree: publication of the local branch
    # is not established, and no current full-suite run was performed here.
    if claim["id"] == 1:
        return "EXTERNALLY_BLOCKED"
    if claim["id"] == 2:
        return "UNVERIFIED"
    if closure.get("status") == "VERIFIED":
        return "VERIFIED_IMPLEMENTATION"
    verdict = str(closure.get("paper_verdict") or "")
    if "CONTRADICTED" in verdict:
        return "CONTRADICTED_BY_CURRENT_EVIDENCE"
    if claim.get("scope") in {"DATA", "EXTERNAL", "TOOLS", "PENDING-PUBLICATION"}:
        return "EXTERNALLY_BLOCKED"
    return "UNVERIFIED"


def _command_for(claim_id: int) -> str:
    if claim_id in {3, 4, 5, 6, 7, 8}:
        return "python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root . --strict"
    if claim_id in {18, 23, 28}:
        return "python scripts/reproduce/audit_calibration_cost_evidence.py --root ."
    if claim_id in {13, 14, 21, 22, 29}:
        return "python benchmark/run_honest_experiments.py --results-dir <offline-results-dir>"
    return "python scripts/reproduce_paper.py --require-claim-closure"


def _next_action(status: str, closure: dict[str, Any]) -> str:
    unmet = closure.get("requirements_unmet") or []
    if unmet:
        return str(unmet[0])
    if status == "VERIFIED_IMPLEMENTATION":
        return "Preserve the implementation evidence; do not promote it to a population claim."
    if status == "CONTRADICTED_BY_CURRENT_EVIDENCE":
        return "Reword or remove the contradicted paper sentence; do not tune evidence to the target."
    return "Review the retained evidence and acquire the explicitly missing external input before rerunning."


def _resolution_mode(status: str, claim: dict[str, Any]) -> str:
    if status == "VERIFIED_IMPLEMENTATION":
        return "CLOSED_LOCAL_SCOPE"
    if status == "CONTRADICTED_BY_CURRENT_EVIDENCE":
        return "LOCAL_REWORD_OR_REMOVE"
    if status == "UNVERIFIED":
        return "LOCAL_REVIEW_OR_CURRENT_RUN"
    if claim.get("scope") == "EXTERNAL":
        return "EXTERNAL_AUTHORIZATION_OR_PROVIDER"
    return "EXTERNAL_DATA_OR_INDEPENDENT_REVIEW"


def _acceptance_criteria(claim: dict[str, Any], closure: dict[str, Any], status: str) -> list[str]:
    criteria = [
        "All listed acceptance tests pass on the target code revision.",
        "Every required artifact exists, is hash-bound where applicable, and its identity matches the declared dataset/split.",
    ]
    if status == "VERIFIED_IMPLEMENTATION":
        criteria.append("Report only the implementation scope stated in verification_result; do not promote it to a population result.")
    elif status == "CONTRADICTED_BY_CURRENT_EVIDENCE":
        criteria.append("Remove or reword the contradicted sentence unless a new preregistered evidence package overturns the contradiction.")
    else:
        criteria.append("The missing prerequisite is supplied without changing frozen inputs, target metrics, denominators, or acceptance rules.")
    if closure.get("paper_verdict"):
        criteria.append("Resolve the recorded paper verdict: " + str(closure["paper_verdict"]))
    return criteria


def _claim_row(root: Path, claim: dict[str, Any], closure: dict[str, Any], revision: str | None) -> dict[str, Any]:
    status = _status(claim, closure)
    evidence = [item.get("path") for item in closure.get("evidence", []) if isinstance(item, dict)]
    if claim["id"] == 15:
        evidence.append("reports/reconciliation/recovered_trace_audit.json")
        evidence.append("reports/reconciliation/recovered_trace_inventory_20261019.json")
        evidence.append("reports/research_results/recovered_trace_localization_20261019.json")
    artifacts = _unique(evidence + list(claim.get("tests", [])))
    return {
        "id": claim["id"],
        "paper_wording": claim["claim"],
        "wording_source": "benchmark/claim_registry.py canonical title; full paper sentence is not retained here",
        "category": CATEGORY_BY_ID.get(claim["id"], "unclassified"),
        "status": status,
        "resolution_mode": _resolution_mode(status, claim),
        "registry_scope": claim["scope"],
        "required_evidence": claim["required_evidence"],
        "minimum_resolution_artifact": (
            (closure.get("requirements_unmet") or [claim["required_evidence"]])[0]
        ),
        "objectively_checkable_acceptance_criteria": _acceptance_criteria(claim, closure, status),
        "existing_artifacts": artifacts,
        "generating_code": _unique([
            "benchmark/claim_registry.py",
            *claim.get("tests", []),
            _command_for(claim["id"]),
        ]),
        "command": _command_for(claim["id"]),
        "code_revision": revision,
        "dataset_revision": "benchmark/cohort_manifest.json and retained frozen/evidence snapshots",
        "missing_prerequisites": closure.get("requirements_unmet", []),
        "next_executable_action": _next_action(status, closure),
        "verification_result": {
            "historical_status": closure.get("status"),
            "current_checkpoint_status": (
                "NOT_RUN_FULL_SUITE" if claim["id"] == 2 else "SCOPE_REVIEWED_FROM_RETAINED_EVIDENCE"
            ),
            "verification_scope": closure.get("verification_scope"),
            "reason": closure.get("reason"),
            "paper_verdict": closure.get("paper_verdict"),
            "acceptance_tests": closure.get("acceptance_tests", []),
        },
    }


def build_ledger(root: Path = ROOT) -> dict[str, Any]:
    from benchmark.claim_registry import CLAIMS
    from benchmark.validate_cohort_manifest import audit_manifest

    closure_dir = root / "reports/claim_closure/claims"
    rows = []
    for claim in CLAIMS:
        closure_path = closure_dir / f"{claim['id']:02d}.json"
        closure = _read_json(root, closure_path.relative_to(root).as_posix())
        rows.append(_claim_row(root, claim, closure, _git_revision(root)))

    manifest = _read_json(root, "benchmark/cohort_manifest.json")
    batch_e = _read_json(root, "reports/new_batches/batchE/scoring.json")
    versioned_cohorts = []
    for manifest_path in sorted((root / "benchmark/versions").glob("*/cohort_manifest.json")):
        audited = audit_manifest(manifest_path, root)
        versioned_cohorts.append({
            "manifest": manifest_path.relative_to(root).as_posix(),
            "schema": audited["schema"],
            "input_rows": audited["input_rows"],
            "accepted_rows": audited["accepted_rows"],
            "remaining_to_target": audited["additional_verified_rows_needed"],
            "status": audited["status"],
            "not_independent_human_review": audited["declared_not_independent_human_review"],
            "chains": audited["chain_counts"],
        })
    counts = {status: sum(row["status"] == status for row in rows) for status in sorted(STATUSES)}
    return {
        "schema_version": 1,
        "objective": "Close paper claims with reproducible evidence or precise blockers; never promote unsupported empirical results.",
        "code_revision": _git_revision(root),
        "status_vocabulary": sorted(STATUSES),
        "claim_counts": counts,
        "claims": rows,
        "current_cohort": {
            "manifest": "benchmark/cohort_manifest.json",
            "target_count": manifest.get("target_count"),
            "accepted_count": manifest.get("accepted_count"),
            "remaining_to_target": manifest.get("remaining_to_target"),
            "not_independent_human_review": manifest.get("not_independent_human_review"),
            "chains": manifest.get("chains"),
        },
        "versioned_cohorts": versioned_cohorts,
        "frozen_batch_e": {
            "artifact": "reports/new_batches/batchE/scoring.json",
            "status": batch_e.get("status"),
            "n": batch_e.get("n"),
            "recall_at_1": batch_e.get("metrics", {}).get("R@1", {}).get("recall"),
            "recall_at_3": batch_e.get("metrics", {}).get("R@3", {}).get("recall"),
            "recall_at_5": batch_e.get("metrics", {}).get("R@5", {}).get("recall"),
            "preservation": "frozen; not rerun, retuned, rescored, renamed, or overwritten",
        },
        "external_effects": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", type=Path, help="Write the ledger to this path instead of stdout")
    args = parser.parse_args(argv)
    ledger = build_ledger(args.root.resolve())
    encoded = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    if args.write:
        destination = args.write if args.write.is_absolute() else args.root / args.write
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Keep the generated artifact LF-stable on Windows and Linux.
        destination.write_bytes(encoded.encode("utf-8"))
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
