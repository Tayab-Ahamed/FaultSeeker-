"""Offline function-level diagnosis over the saved 23-row Batch A replay inputs."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
RAW = ROOT / "reports/new_batches/batchA_adapterfix4/rpc_publicnode_raw/eth"
FINAL_RAW = ROOT / "reports/new_batches/batchA_adapterfix4/rpc_drpc_final/eth"
PRODUCER_COMMIT = "1b1c7395771663622dd14b9731b4b8b471221960"
MODEL = "llm-free-function-ranker"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_semantics(label: dict[str, Any]) -> dict[str, str]:
    text = " ".join(str(label.get(key, "")) for key in ("source_transaction_quote", "vulnerable_contract_quote", "vulnerable_function_quote"))
    lower = text.lower()
    if "attacker was call" in lower or "attacker called" in lower:
        return {"category": "exploit_entry_call", "evidence": label.get("vulnerable_function_quote", "")}
    if any(token in lower for token in ("root cause", "vulnerability", "vulnerable", "lacks access control", "will burn token")):
        return {"category": "internal_vulnerable_function", "evidence": label.get("vulnerable_function_quote", "")}
    return {"category": "other", "evidence": label.get("vulnerable_function_quote", "")}


def main() -> int:
    producer_root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(producer_root))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.utils.rpc_provider import normalize_trace_node

    ranker_module = load_module("diag_current_ranker", ROOT / "faultseeker/function_analysis/function_ranker.py")
    loc = load_module("diag_current_localization", ROOT / "benchmark/honest_eval/localization.py")
    ranker = ranker_module.FunctionRanker
    batch = load(BATCH)
    valid = load(VALID)
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    loc._register_fn_names(str(row["vulnerable_function"]) for row in batch["rows"])
    rows = []
    for record in valid["records"]:
        tx = str(record["transaction_hash"]).lower()
        final_path = FINAL_RAW / f"{tx}.json"
        if final_path.is_file():
            raw = load(final_path)
            tx_response = raw["transaction_response"]["response"]
            receipt_response = raw["receipt_response"]["response"]
        else:
            raw = load(RAW / f"{tx}.json")
            tx_response = raw["transaction_response"]
            receipt_response = raw["receipt_response"]
        structured = {
            "transaction_hash": tx,
            "chain": "eth",
            "trace": normalize_trace_node(record["trace"]),
            "storage_events": [], "storage_reads": [], "state_diff": {},
            "trace_coverage": {"trace_complete": True, "storage_trace_complete": False, "token_flow_complete": False, "multi_tx_context_complete": False},
        }
        orchestrator = ForensicsOrchestrator(
            model=MODEL,
            txn_sequencer=_CapturedSequencer(structured),
            txn_info_collector=_CapturedInfo(tx_response["result"], receipt_response["result"], tx, "eth"),
        )
        result, _, _ = orchestrator.run(tx, "eth")
        tx_analysis = {"repeated_patterns": result.repeated_patterns, "function_call_loc_memo": result.function_call_loc_memo}
        predictions = [dict(item) for item in ranker().rank(result, tx_analysis).ranked_functions]
        label = labels[tx]
        address = loc._norm_addr(str(label["vulnerable_contract"]))
        raw_label_function = str(label["vulnerable_function"])
        normalized_label_function = loc._norm_fn(raw_label_function)
        at_address = [p for p in predictions if loc._norm_addr(p.get("code_address") or p.get("address")) == address]
        top5 = []
        for prediction in at_address[:5]:
            selector = str(prediction.get("selector") or prediction.get("function") or "")
            resolved = loc._selector_to_name(selector) if selector.startswith("0x") and len(selector) == 10 else None
            top5.append({"rank": prediction.get("rank"), "function_name": resolved or None, "selector": selector, "resolved_to_name": resolved is not None})
        selectors = {item["selector"] for item in top5}
        # The frozen Batch A artifact stores function names/signatures, not selectors.
        # Report the scorer's actual comparison basis rather than inventing an ABI selector.
        resolved_names = {item["function_name"] for item in top5 if item["function_name"]}
        if normalized_label_function in resolved_names:
            comparison_basis = "name vs name"
        elif top5:
            comparison_basis = "selector vs name"
        else:
            comparison_basis = "no candidate key at labeled address"
        candidate_label_present = normalized_label_function in resolved_names
        semantics = source_semantics(label)
        if semantics["category"] == "exploit_entry_call":
            classification = "c"
        elif candidate_label_present and comparison_basis == "selector vs name":
            classification = "a"
        elif candidate_label_present:
            classification = "d"
        else:
            classification = "b"
        rows.append({
            "transaction_hash": tx,
            "label": {"address": label["vulnerable_contract"], "function": raw_label_function, "source_path": label["source_path"], "source_poc_url": label["source_poc_url"], "source_transaction_quote": label["source_transaction_quote"], "source_function_quote": label["vulnerable_function_quote"]},
            "semantic_location": semantics,
            "top5_at_labeled_address": top5,
            "candidate_selector_equal_to_label_selector": {"status": "not_stored_in_frozen_label", "selectors_at_address": sorted(selectors)},
            "function_key_comparison": {"label_key": normalized_label_function, "basis": comparison_basis, "candidate_resolved_names_at_address": sorted(resolved_names)},
            "classification": classification,
            "candidate_count": len(predictions),
        })
        print(f"diagnosed {len(rows)}/{len(valid['records'])}")
    counts = {key: sum(row["classification"] == key for row in rows) for key in ("a", "b", "c", "d")}
    examples = {key: [row["transaction_hash"] for row in rows if row["classification"] == key][:3] for key in counts}
    result = {"label": "function-level diagnosis, read-only", "producer_replay_source": "reports/new_batches/batchA_adapterfix4/rpc_drpc_final/eth/", "producer_commit": PRODUCER_COMMIT, "network_calls": False, "rescoring_or_tuning": False, "rows": rows, "classification_counts": counts, "classification_examples": examples, "notes": ["The frozen Batch A function labels contain names/signatures, not selectors.", "Selector equality to a labeled selector is therefore reported as not stored rather than inferred from an ABI.", "Candidate lists were generated offline from the saved raw inputs; no RPC or new result file was read or modified."]}
    (OUT / "function_diagnosis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Batch A function-level diagnosis", "", "**Label: function-level diagnosis, read-only**", "", f"Producer-era source commit: `{PRODUCER_COMMIT}`", "", "## Classification counts", "", "| Class | Count | Examples |", "| --- | ---: | --- |"]
    descriptions = {"a": "label function present in candidates but key format differs", "b": "label function absent from candidates at that address", "c": "label is semantically a different kind of function than the benchmark ground truth", "d": "other"}
    for key in ("a", "b", "c", "d"):
        lines.append(f"| {key} — {descriptions[key]} | {counts[key]} | {', '.join(examples[key]) or 'N/A'} |")
    lines += ["", "## Per-row details", "", "| Transaction | Label function | Source | Semantic location | Top-5 at labeled address | Key basis | Class |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        top = "; ".join(f"r{item['rank']}:{item['function_name'] or '-'} [{item['selector']}] ({'resolved' if item['resolved_to_name'] else 'unresolved'})" for item in row["top5_at_labeled_address"])
        lines.append(f"| `{row['transaction_hash']}` | `{row['label']['function']}` | `{row['label']['source_path']}` | {row['semantic_location']['category']} | {top or 'none'} | {row['function_key_comparison']['basis']} | {row['classification']} |")
    lines += ["", "The complete label source text, exact address casing, selector-equality status, and per-row candidate details are in `function_diagnosis.json`.", ""]
    (OUT / "function_diagnosis.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
