"""Evidence-separated evaluation for synthetic mechanisms and real replays.

This module deliberately keeps mechanism fixtures and historical captures in
different accounting buckets.  Synthetic and compiled-local executions can
prove that the implementation behaves as designed, but they are never merged
into empirical cohort metrics.  Historical replay artifacts are counted only
when their receipt, normalization, and artifact integrity checks pass; the
retained captures still remain ineligible for incident metrics because they do
not contain independent adjudication.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from benchmark.detector_experiments import detector_observation


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPILED_FIXTURE = ROOT / "reports/live_verification/compiled_evm_trace.json"
DEFAULT_REPLAY_SUMMARIES = (
    ROOT / "reports/historical_replay/historical_replay_summary.json",
    ROOT / "reports/claim_closure/comparison_attempt_2/historical_replay_summary.json",
)


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    label: bool
    mechanism: str
    capture: dict[str, Any]
    expected: dict[str, Any]


def _address(char: str) -> str:
    return "0x" + char * 40


def _call(caller: str, callee: str, selector: str, children: list[dict[str, Any]] | None = None,
          call_type: str = "CALL") -> dict[str, Any]:
    return {
        "from": caller,
        "to": callee,
        "input": selector + "00" * 4 if selector != "0x" else "0x",
        "type": call_type,
        "calls": children or [],
    }


def _recursive_call(vault: str, attacker: str, outer_selector: str = "0xdeadbeef",
                    inner_selector: str | None = None) -> dict[str, Any]:
    return _call(
        _address("a"),
        vault,
        outer_selector,
        [_call(vault, attacker, "0x", [
            _call(attacker, vault, inner_selector or outer_selector)
        ])],
    )


def _structural_capture(root: dict[str, Any]) -> dict[str, Any]:
    return {"raw_trace": {"call": root}}


def synthetic_cases() -> list[SyntheticCase]:
    """Return deterministic call-graph cases with no population claims."""
    vault = _address("1")
    attacker = _address("2")
    quiet = _address("3")

    return [
        SyntheticCase(
            case_id="recursive_same_function",
            label=True,
            mechanism="external_callback_then_same_selector",
            capture=_structural_capture(_recursive_call(vault, attacker)),
            expected={"detector_variant": "structural", "predicted_exploit": True,
                      "fallback_mode": True},
        ),
        SyntheticCase(
            case_id="recursive_cross_function",
            label=True,
            mechanism="external_callback_then_different_selector",
            capture=_structural_capture(
                _recursive_call(vault, attacker, "0xaaaaaaaa", "0xbbbbbbbb")),
            expected={"detector_variant": "structural", "predicted_exploit": False,
                      "tier": "POSSIBLE_REENTRANCY", "fallback_mode": True},
        ),
        SyntheticCase(
            case_id="guarded_callback",
            label=False,
            mechanism="callback_without_same_contract_reentry",
            capture=_structural_capture(_call(
                _address("a"), vault, "0xaaaaaaaa",
                [_call(vault, quiet, "0x", [_call(quiet, _address("4"), "0xbbbbbbbb")])],
            )),
            expected={"detector_variant": "structural", "predicted_exploit": False,
                      "fallback_mode": True},
        ),
        SyntheticCase(
            case_id="plain_external_call",
            label=False,
            mechanism="single_external_call_no_reentry",
            capture=_structural_capture(_call(_address("a"), vault, "0xaaaaaaaa",
                                               [_call(vault, quiet, "0x")])) ,
            expected={"detector_variant": "structural", "predicted_exploit": False,
                      "fallback_mode": True},
        ),
    ]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_synthetic_cases(cases: Iterable[SyntheticCase] | None = None) -> list[dict[str, Any]]:
    """Run hand-authored cases through the same structural detector adapter."""
    results = []
    for case in cases or synthetic_cases():
        variant = case.expected["detector_variant"]
        observation = detector_observation(case.capture, variant)
        detail = observation["detector_result"]
        result = {
            "case_id": case.case_id,
            "source_kind": "synthetic_fixture",
            "synthetic": True,
            "ground_truth_origin": "hand-authored-mechanism",
            "label": case.label,
            "mechanism": case.mechanism,
            "detector_variant": variant,
            "predicted_exploit": observation["predicted_exploit"],
            "tier": detail.get("tier"),
            "score": detail.get("score"),
            "fallback_mode": detail.get("context", {}).get("fallback_mode"),
            "input_sha256": observation["input_sha256"],
            "metric_eligible": False,
            "metric_ineligibility_reason": "synthetic_mechanism_case",
        }
        _assert_expected(result, case.expected)
        result["result_sha256"] = _digest(result)
        results.append(result)
    return results


def run_compiled_fixture_cases(path: Path = DEFAULT_COMPILED_FIXTURE) -> list[dict[str, Any]]:
    """Evaluate the checked-in compiler/Anvil artifact without mixing it into real data."""
    if not path.is_file():
        return []
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("authentic_execution") is not True:
        raise ValueError("compiled fixture must declare authentic_execution=true")
    results = []
    for case_id, case in sorted(artifact.get("cases", {}).items()):
        observation = detector_observation(
            {"raw_trace": {"call": case["call_trace"], "opcode": case["opcode_trace"]}},
            "full",
        )
        detail = observation["detector_result"]
        result = {
            "case_id": case_id,
            "source_kind": "compiled_evm_fixture",
            "synthetic": True,
            "ground_truth_origin": "compiled-local-contract",
            "detector_variant": "full",
            "predicted_exploit": observation["predicted_exploit"],
            "tier": detail.get("tier"),
            "score": detail.get("score"),
            "input_sha256": observation["input_sha256"],
            "artifact_sha256": _digest(case),
            "metric_eligible": False,
            "metric_ineligibility_reason": "compiled_fixture_not_population_data",
        }
        results.append(result)
    return results


def _assert_expected(result: dict[str, Any], expected: dict[str, Any]) -> None:
    for key, value in expected.items():
        if key == "detector_variant":
            continue
        actual = result.get(key)
        if actual != value:
            raise AssertionError(f"{result['case_id']}: expected {key}={value!r}, got {actual!r}")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _artifact_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_capture_artifact(summary_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    artifact_name = case.get("artifact")
    if not isinstance(artifact_name, str) or not artifact_name:
        return {"artifact_present": False, "artifact_valid": False,
                "artifact_sha256": None, "artifact_error": "missing_artifact_name"}
    artifact_path = (summary_path.parent / artifact_name).resolve()
    if not artifact_path.is_relative_to(summary_path.parent.resolve()):
        return {"artifact_present": False, "artifact_valid": False,
                "artifact_sha256": None, "artifact_error": "artifact_escapes_summary_directory"}
    if not artifact_path.is_file():
        return {"artifact_present": False, "artifact_valid": False,
                "artifact_sha256": None, "artifact_error": "artifact_not_found"}
    digest = _artifact_digest(artifact_path)
    expected_digest = case.get("artifact_sha256")
    digest_matches = expected_digest in (None, "", digest)
    try:
        with gzip.open(artifact_path, "rt", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        payload_valid = isinstance(payload, dict)
    except (OSError, ValueError):
        payload_valid = False
    return {
        "artifact_present": True,
        "artifact_valid": bool(digest_matches and payload_valid),
        "artifact_sha256": digest,
        "artifact_error": None if digest_matches and payload_valid else "artifact_digest_or_json_invalid",
    }


def load_replay_accounting(paths: Iterable[Path] = DEFAULT_REPLAY_SUMMARIES) -> dict[str, Any]:
    """Load retained replay summaries into an evidence-only accounting report."""
    runs = []
    captures = []
    seen: set[tuple[str, str]] = set()
    for path in paths:
        path = Path(path)
        if not path.is_file():
            continue
        summary = _load_json(path)
        usage = summary.get("rpc_usage") if isinstance(summary.get("rpc_usage"), dict) else {}
        runs.append({
            "summary_path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
            "status": summary.get("status"),
            "scope": summary.get("scope"),
            "rpc_requests": usage.get("outbound_rpc_requests"),
            "estimated_cost_usd": usage.get("estimated_cost_usd"),
            "billing_confirmed": usage.get("billing_confirmed") is True,
        })
        for case in summary.get("cases", []):
            txn_hash = str(case.get("transaction_hash") or "").lower()
            identity = ("eth", txn_hash)
            artifact = _validate_capture_artifact(path, case)
            duplicate = identity in seen
            seen.add(identity)
            capture_valid = bool(
                txn_hash.startswith("0x") and len(txn_hash) == 66
                and case.get("normalization_complete") is True
                and case.get("storage_owners_verified") is True
                and case.get("receipt_matches") is True
                and artifact["artifact_valid"]
                and not duplicate
            )
            captures.append({
                "identity": f"eth:{txn_hash}",
                "transaction_hash": txn_hash,
                "chain": "eth",
                "source_kind": "recorded_historical",
                "synthetic": False,
                "status": "CAPTURED" if capture_valid else "INVALID_CAPTURE",
                "normalization_complete": case.get("normalization_complete") is True,
                "storage_owners_verified": case.get("storage_owners_verified") is True,
                "receipt_matches": case.get("receipt_matches") is True,
                "opcode_count": case.get("opcode_count"),
                "sload_count": case.get("sload_count"),
                "sstore_count": case.get("sstore_count"),
                **artifact,
                "duplicate": duplicate,
                "metric_eligible": False,
                "metric_ineligibility_reason": "independent_incident_adjudication_absent",
            })
    valid = [row for row in captures if row["status"] == "CAPTURED"]
    return {
        "scope": "recorded historical opcode captures, not incident adjudication",
        "runs": runs,
        "captures": captures,
        "summary": {
            "runs": len(runs),
            "captures_seen": len(captures),
            "valid_captures": len(valid),
            "metric_eligible_captures": sum(row["metric_eligible"] for row in captures),
            "chains": sorted({row["chain"] for row in valid}),
        },
    }


def build_report(
    compiled_fixture: Path = DEFAULT_COMPILED_FIXTURE,
    replay_summaries: Iterable[Path] = DEFAULT_REPLAY_SUMMARIES,
) -> dict[str, Any]:
    synthetic = run_synthetic_cases()
    compiled = run_compiled_fixture_cases(compiled_fixture)
    replay = load_replay_accounting(replay_summaries)
    return {
        "schema_version": 1,
        "evaluation_contract": {
            "synthetic_metric_eligible": False,
            "real_metric_requires_independent_adjudication": True,
            "paper_files_modified": False,
        },
        "synthetic": {
            "cases": synthetic,
            "compiled_evm_cases": compiled,
            "case_count": len(synthetic) + len(compiled),
        },
        "real_replay": replay,
        "claim_gate": {
            "real_population_metrics": "BLOCKED",
            "reason": "retained captures lack independent incident adjudication",
            "synthetic_results_are_not_empirical": True,
        },
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "SyntheticCase",
    "build_report",
    "load_replay_accounting",
    "run_compiled_fixture_cases",
    "run_synthetic_cases",
    "synthetic_cases",
    "write_report",
]
