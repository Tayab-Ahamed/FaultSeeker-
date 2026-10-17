"""Read-only Batch A control and ranking diagnostic.

This diagnostic imports the already-frozen Batch A adapter and ranker call but
writes all new material only beside this file. It never changes frozen inputs,
ranker code, scorer code, or existing reports.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VALID_SET = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
MINING_MANIFEST = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/manifest.json"
ORIGINAL_MANIFEST = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json"
ORIGINAL_RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
ORIGINAL_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
TRACE_ROOT = ROOT / "reports/cohort_rebuild_v2/traces"
EXPECTED_BATCH_SHA = "4a971c4576173b9b67f51a42d4c99583a7dad704fec4492cc6ee937eb227aa21"
EXPECTED_VALID_SHA = "fedcca0de8381a4fa67ab01d68d02c664261c07542de3aa76c09f9a66fc6d785"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.honest_eval.localization import (  # noqa: E402
    _keccak256,
    _norm_addr,
    _norm_fn,
    _parse_location_entry,
    _prediction_keys,
    _register_fn_names,
    _selector_to_name,
    rank_of_first_hit,
    LocalizationTarget,
)
from scripts.research.evaluate_batch_a_ranker_once import _first_rank, _rank_one  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def checksum_address(address: str) -> str:
    low = _norm_addr(address).removeprefix("0x")
    digest = _keccak256(low.encode("ascii")).hex()
    return "0x" + "".join(ch.upper() if ch in "abcdef" and int(digest[i], 16) >= 8 else ch for i, ch in enumerate(low))


def recursive_nodes(node: dict[str, Any]):
    yield node
    for child in node.get("calls", []) or []:
        if isinstance(child, dict):
            yield from recursive_nodes(child)


def trace_addresses(trace: dict[str, Any]) -> dict[str, Any]:
    nodes = list(recursive_nodes(trace))
    tos = [_norm_addr(n.get("to", "")) for n in nodes if n.get("to")]
    froms = [_norm_addr(n.get("from", "")) for n in nodes if n.get("from")]
    return {"nodes": nodes, "to": tos, "from": froms, "all": set(tos) | set(froms)}


def batch_labels() -> dict[str, dict[str, Any]]:
    payload = load_json(BATCH)
    assert payload["artifact_sha256"] == EXPECTED_BATCH_SHA
    body = dict(payload)
    body.pop("artifact_sha256", None)
    assert hashlib.sha256((json.dumps(body, indent=2, sort_keys=True) + "\n").encode()).hexdigest() == EXPECTED_BATCH_SHA
    labels = {str(row["transaction_hash"]).lower(): row for row in payload["rows"]}
    _register_fn_names(str(row["vulnerable_function"]) for row in labels.values())
    return labels


def target_from_gt(path: Path) -> LocalizationTarget:
    raw = load_json(path)
    target = LocalizationTarget(txn_hash=path.stem, name=str(raw.get("name") or ""))
    names = []
    for key, values in (raw.get("location") or {}).items():
        for entry in [key] + list(values or []):
            parsed = _parse_location_entry(entry)
            if not parsed:
                continue
            address, member, is_line = parsed
            if not is_line:
                target.functions.add((address, member))
                names.append(member)
    _register_fn_names(names)
    return target


def first_address_rank(predictions: list[dict[str, Any]], address: str) -> int | None:
    target = _norm_addr(address)
    for index, prediction in enumerate(predictions, start=1):
        predicted, _ = _prediction_keys(prediction)
        if predicted and predicted[0] == target:
            return index
    return None


def format_diagnostic(label: dict[str, Any], trace: dict[str, Any], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    address = _norm_addr(label["vulnerable_contract"])
    function = _norm_fn(label["vulnerable_function"])
    info = trace_addresses(trace)
    at_label = [n for n in info["nodes"] if _norm_addr(n.get("to", "")) == address]
    selectors = []
    resolved = []
    other_same_function_addresses = set()
    for node in info["nodes"]:
        data = node.get("input") or ""
        selector = data[:10].lower() if isinstance(data, str) and len(data) >= 10 and data.startswith("0x") else None
        if _norm_addr(node.get("to", "")) == address and selector:
            selectors.append(selector)
            name = _selector_to_name(selector)
            if name:
                resolved.append(name)
        if selector and _selector_to_name(selector) == function and _norm_addr(node.get("to", "")) != address:
            other_same_function_addresses.add(_norm_addr(node.get("to", "")))
    source_addresses = [a.lower() for a in re.findall(r"0x[0-9a-fA-F]{40}", label.get("vulnerable_contract_quote", ""))]
    source_address = source_addresses[0] if source_addresses else None
    source_checksum = checksum_address(source_address) if source_address else None
    source_case_matches_checksum = bool(source_address and source_checksum.lower() == source_address and source_checksum == re.findall(r"0x[0-9a-fA-F]{40}", label.get("vulnerable_contract_quote", ""))[0])
    return {
        "label_address": address,
        "label_function": function,
        "address_case": "normalized_case_equivalent" if source_address == address else "no_source_address_or_not_equivalent",
        "label_is_lowercase": str(label["vulnerable_contract"]) == str(label["vulnerable_contract"]).lower(),
        "source_address": source_checksum if source_address else None,
        "source_checksum_valid": source_case_matches_checksum,
        "selectors_at_label_address": sorted(set(selectors)),
        "resolved_functions_at_label_address": sorted(set(resolved)),
        "function_selector_match": function in set(resolved) if at_label else None,
        "possible_proxy_or_implementation_mismatch": bool(address not in info["all"] and other_same_function_addresses),
        "other_addresses_with_labeled_function_selector": sorted(other_same_function_addresses),
        "address_in_trace": address in info["all"],
        "address_in_trace_to": address in set(info["to"]),
        "address_rank_full_list": first_address_rank(predictions, address),
        "function_rank_full_list": _first_rank(predictions, address, function, address_sensitive=False),
        "address_function_rank_full_list": _first_rank(predictions, address, function, address_sensitive=True),
        "candidate_count": len(predictions),
    }


def classify(diag: dict[str, Any]) -> str:
    if not diag["address_in_trace"]:
        return "label_not_in_trace"
    if diag["function_selector_match"] is False and diag["selectors_at_label_address"]:
        return "adapter_or_format_mismatch"
    return "label_in_trace_but_ranked_low"


def control_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    original = load_json(ORIGINAL_MANIFEST)
    ok_ids = [str(row["txn_hash"]).lower() for row in original["rows"] if row.get("status") == "ok"]
    candidates = []
    for path in sorted(TRACE_ROOT.rglob("*.json.gz")):
        tx = path.name.split(".json.gz")[0].lower()
        if tx not in ok_ids:
            continue
        raw_path = ORIGINAL_RAW / f"{tx}.json"
        if not raw_path.is_file():
            continue
        gt_path = ORIGINAL_GT / f"{tx}.json"
        if not gt_path.is_file():
            continue
        candidates.append((tx, path, raw_path, gt_path))
    selected = candidates[:10]
    controls = []
    for tx, trace_path, known_path, gt_path in selected:
        with gzip.open(trace_path, "rt", encoding="utf-8") as handle:
            captured = json.load(handle)
        trace = captured["raw_trace"]["call"]
        known = load_json(known_path)
        target = target_from_gt(gt_path)
        predictions = _rank_one({"transaction_hash": tx, "chain": captured["chain"], "trace": trace})
        known_rank = known.get("score", {}).get("first_hit_rank")
        adapter_rank = rank_of_first_hit(target, predictions, match="function")
        controls.append({
            "transaction_hash": tx,
            "chain": captured["chain"],
            "trace_artifact": trace_path.relative_to(ROOT).as_posix(),
            "known_prediction_artifact": known_path.relative_to(ROOT).as_posix(),
            "known_rank": known_rank,
            "adapter_rank": adapter_rank,
            "rank_reproduced": known_rank == adapter_rank,
            "known_prediction_count": len(known.get("predictions", [])),
            "adapter_prediction_count": len(predictions),
        })
    return controls, {
        "requested": 10,
        "available_local_full_traces_with_known_ranks": len(candidates),
        "executed": len(controls),
        "blocked_missing_local_control_artifacts": max(0, 10 - len(controls)),
        "blocked_reason": "The remaining original-110 rows have saved ranks but no local full callTracer artifact; no RPC was used to fill the gap.",
    }


def main() -> None:
    labels = batch_labels()
    valid = load_json(VALID_SET)
    assert sha256(VALID_SET) == EXPECTED_VALID_SHA
    controls, control_summary = control_rows()
    control_summary["diagnosis"] = "adapter_control_failed" if any(not row["rank_reproduced"] for row in controls) else "adapter_control_reproduced"
    rows = []
    for record in valid["records"]:
        tx = str(record["transaction_hash"]).lower()
        label = labels[tx]
        predictions = _rank_one(record)
        diagnostic = format_diagnostic(label, record["trace"], predictions)
        diagnostic["classification"] = classify(diagnostic)
        diagnostic.update({
            "sequence": record.get("sequence"),
            "chain": record["chain"],
            "transaction_hash": tx,
        })
        rows.append(diagnostic)
    class_counts = Counter(row["classification"] for row in rows)
    format_summary = {
        "address_case_normalized_equivalent": sum(row["address_case"] == "normalized_case_equivalent" for row in rows),
        "source_checksum_valid": sum(row["source_checksum_valid"] for row in rows),
        "source_checksum_invalid_or_unavailable": sum(not row["source_checksum_valid"] for row in rows),
        "function_selector_match_true": sum(row["function_selector_match"] is True for row in rows),
        "function_selector_match_false": sum(row["function_selector_match"] is False for row in rows),
        "function_selector_match_unavailable": sum(row["function_selector_match"] is None for row in rows),
        "possible_proxy_or_implementation_mismatch": sum(row["possible_proxy_or_implementation_mismatch"] for row in rows),
    }
    examples = {name: [row for row in rows if row["classification"] == name][:3] for name in sorted(class_counts)}
    result = {
        "label": "diagnostic only; no tuning; no new scoring claim",
        "frozen_inputs": {
            "batch_path": str(BATCH.relative_to(ROOT)).replace("\\", "/"),
            "batch_canonical_sha256": EXPECTED_BATCH_SHA,
            "valid_set_path": str(VALID_SET.relative_to(ROOT)).replace("\\", "/"),
            "valid_set_sha256": EXPECTED_VALID_SHA,
            "mining_manifest": str(MINING_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        },
        "control": {"summary": control_summary, "rows": controls},
        "batch_a": {
            "rows": rows,
            "counts_by_class": dict(sorted(class_counts.items())),
            "format_summary": format_summary,
            "examples_by_class": examples,
        },
        "method": {
            "adapter_path": "scripts/research/evaluate_batch_a_ranker_once.py::_rank_one",
            "ranker_path": "faultseeker/function_analysis/function_ranker.py",
            "rank_definition": "1-based full candidate-list rank; address rank ignores function; function rank ignores address; pair rank uses both",
            "trace_address_definition": "label address present in any callTracer from/to field; to-field is reported separately",
            "format_checks": "lowercase normalization, source-address checksum comparison, selector-to-name resolution, and evidence-bounded proxy/implementation signal",
            "network_calls": False,
            "ranker_or_scorer_changes": False,
        },
    }
    (OUT / "diagnostic.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# Batch A control and diagnostic",
        "",
        "Diagnostic only; no tuning; no new scoring claim.",
        "",
        "## Control",
        "",
        f"Requested 10 original-110 controls; executed {control_summary['executed']}; blocked {control_summary['blocked_missing_local_control_artifacts']} due missing local full callTracer artifacts. Diagnosis: `{control_summary['diagnosis']}`.",
        "",
        "| Transaction | Known rank | Adapter rank | Reproduced |",
        "|---|---:|---:|---|",
    ]
    for row in controls:
        lines.append(f"| `{row['transaction_hash']}` | {row['known_rank']} | {row['adapter_rank']} | {row['rank_reproduced']} |")
    lines += ["", "## Batch A classification counts", ""]
    for name, count in sorted(class_counts.items()):
        lines.append(f"- `{name}`: {count}")
    lines += [
        "",
        "## Format checks",
        "",
        f"- Address casing normalized-equivalent: {format_summary['address_case_normalized_equivalent']}/23",
        f"- Source checksum valid: {format_summary['source_checksum_valid']}/23",
        f"- Function selector resolved to labeled name: {format_summary['function_selector_match_true']}/23",
        f"- Function selector unresolved/mismatched where label address was called: {format_summary['function_selector_match_false']}/23",
        f"- Possible proxy/implementation signal: {format_summary['possible_proxy_or_implementation_mismatch']}/23",
    ]
    lines += ["", "## Examples", ""]
    for name, values in examples.items():
        lines.append(f"### {name}")
        for row in values:
            lines.append(f"- `{row['transaction_hash']}`: address_rank={row['address_rank_full_list']}, function_rank={row['function_rank_full_list']}, pair_rank={row['address_function_rank_full_list']}, candidates={row['candidate_count']}, address_in_trace={row['address_in_trace']}")
        lines.append("")
    (OUT / "diagnostic.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"control": control_summary, "batch_counts": dict(sorted(class_counts.items()))}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
