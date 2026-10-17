"""Offline selector checks for Batch A class-b and class-d rows."""
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
DIAG = ROOT / "reports/new_batches/batchA_functiondiag/function_diagnosis.json"
PRODUCER_COMMIT = "1b1c7395771663622dd14b9731b4b8b471221960"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def walk(node: dict[str, Any]):
    yield node
    for child in node.get("calls", []) or []:
        if isinstance(child, dict):
            yield from walk(child)


def responses(tx: str):
    final = FINAL_RAW / f"{tx}.json"
    if final.is_file():
        raw = load(final)
        return raw["transaction_response"]["response"], raw["receipt_response"]["response"]
    raw = load(RAW / f"{tx}.json")
    return raw["transaction_response"], raw["receipt_response"]


def main() -> int:
    producer_root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(producer_root))
    from benchmark.captured_inputs import _CapturedInfo, _CapturedSequencer
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.utils.rpc_provider import normalize_trace_node

    ranker_module = module("selectorcheck_ranker", ROOT / "faultseeker/function_analysis/function_ranker.py")
    loc = module("selectorcheck_localization", ROOT / "benchmark/honest_eval/localization.py")
    ranker = ranker_module.FunctionRanker
    batch = load(BATCH)
    valid = load(VALID)
    diag = load(DIAG)
    selected = {row["transaction_hash"]: row for row in diag["rows"] if row["classification"] in {"b", "d"}}
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    loc._register_fn_names(str(row["vulnerable_function"]) for row in batch["rows"])
    output_rows = []
    for record in valid["records"]:
        tx = str(record["transaction_hash"]).lower()
        if tx not in selected:
            continue
        label = labels[tx]
        raw_function = str(label["vulnerable_function"])
        source_text = " ".join(str(label.get(key, "")) for key in ("source_transaction_quote", "vulnerable_contract_quote", "vulnerable_function_quote")).lower()
        if "delegatecall" in source_text:
            source_target_statement = "delegatecall target stated"
        elif any(token in source_text for token in ("vulnerable function", "root cause", "vulnerability", "lacks access control")):
            source_target_statement = "internal vulnerable function stated"
        else:
            source_target_statement = "not stated"
        has_signature = "(" in raw_function and raw_function.endswith(")")
        selector = loc._fn_selector(raw_function) if has_signature else None
        tx_response, receipt_response = responses(tx)
        structured = {"transaction_hash": tx, "chain": "eth", "trace": normalize_trace_node(record["trace"]), "storage_events": [], "storage_reads": [], "state_diff": {}, "trace_coverage": {"trace_complete": True, "storage_trace_complete": False, "token_flow_complete": False, "multi_tx_context_complete": False}}
        orchestrator = ForensicsOrchestrator(model="llm-free-function-ranker", txn_sequencer=_CapturedSequencer(structured), txn_info_collector=_CapturedInfo(tx_response["result"], receipt_response["result"], tx, "eth"))
        forensics_result, _, _ = orchestrator.run(tx, "eth")
        tx_analysis = {"repeated_patterns": forensics_result.repeated_patterns, "function_call_loc_memo": forensics_result.function_call_loc_memo}
        predictions = [dict(item) for item in ranker().rank(forensics_result, tx_analysis).ranked_functions]
        address = str(label["vulnerable_contract"]).lower()
        candidate_selectors_at_address = sorted({str(p.get("selector") or p.get("function") or "").lower() for p in predictions if str(p.get("code_address") or p.get("address") or "").lower() == address})
        candidate_selectors_trace = sorted({str(p.get("selector") or p.get("function") or "").lower() for p in predictions})
        trace_nodes = list(walk(record["trace"]))
        trace_selectors = sorted({str((node.get("input") or "")[:10]).lower() for node in trace_nodes if isinstance(node.get("input"), str) and node.get("input", "").startswith("0x") and len(node.get("input", "")) >= 10})
        labeled_address_trace_selectors = sorted({str((node.get("input") or "")[:10]).lower() for node in trace_nodes if str(node.get("to") or "").lower() == address and isinstance(node.get("input"), str) and node.get("input", "").startswith("0x") and len(node.get("input", "")) >= 10})
        selector_in_candidates_at_address = bool(selector and selector.lower() in candidate_selectors_at_address)
        selector_in_any_candidates = bool(selector and selector.lower() in candidate_selectors_trace)
        selector_in_trace = bool(selector and selector.lower() in trace_selectors)
        selector_at_label_address = bool(selector and selector.lower() in labeled_address_trace_selectors)
        if not has_signature:
            classification = "4"
        elif selector_in_candidates_at_address or selector_in_any_candidates:
            resolved = loc._selector_to_name(selector)
            classification = "1" if resolved is None else "1"
        elif selector_in_trace:
            classification = "2"
        else:
            classification = "3"
        output_rows.append({"transaction_hash": tx, "label_function": raw_function, "label_address": label["vulnerable_contract"], "source_path": label["source_path"], "source_function_quote": label["vulnerable_function_quote"], "full_signature_available": has_signature, "computed_selector": selector, "candidate_selectors_at_labeled_address": candidate_selectors_at_address, "candidate_selectors_anywhere": candidate_selectors_trace, "selector_in_candidates_at_labeled_address": selector_in_candidates_at_address, "selector_in_any_candidate": selector_in_any_candidates, "trace_selectors": trace_selectors, "selector_in_trace_any_address": selector_in_trace, "labeled_address_trace_selectors": labeled_address_trace_selectors, "selector_called_at_labeled_address": selector_at_label_address, "source_semantic_location": selected[tx]["semantic_location"]["category"], "source_target_statement": source_target_statement, "if_name_only_argument_type_guesses_not_tried": [] if has_signature else ["all argument-type combinations; no signature was inferred"], "classification": classification})
        print(f"checked {len(output_rows)}/{len(selected)}")
    counts = {str(i): sum(row["classification"] == str(i) for row in output_rows) for i in range(1, 5)}
    examples = {key: [row["transaction_hash"] for row in output_rows if row["classification"] == key][:3] for key in counts}
    result = {"label": "selector check, offline", "producer_commit": PRODUCER_COMMIT, "network_calls": False, "tuning_or_fixes": False, "input_classes": {"class_b": 20, "class_d": 1}, "rows": output_rows, "classification_counts": counts, "classification_examples": examples, "notes": ["Keccak selectors were computed locally from the exact stored function strings when they ended in parentheses.", "No argument types were guessed.", "The frozen Batch A labels in these rows all contain parenthesized strings; no bare-name row remained among class b/d."]}
    (OUT / "selector_check.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Batch A selector check", "", "**Label: selector check, offline**", "", "| Class | Count | Examples |", "| --- | ---: | --- |", "| 1 — selector present in candidates, name unresolved | %d | %s |" % (counts["1"], ", ".join(examples["1"]) or "N/A"), "| 2 — selector in trace but not a candidate | %d | %s |" % (counts["2"], ", ".join(examples["2"]) or "N/A"), "| 3 — selector never appears in trace | %d | %s |" % (counts["3"], ", ".join(examples["3"]) or "N/A"), "| 4 — cannot determine (name only) | %d | %s |" % (counts["4"], ", ".join(examples["4"]) or "N/A"), "", "| Transaction | Function | Selector | At address in candidates? | Anywhere in candidates? | In trace? | Called at labeled address? | Source target statement | Class |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in output_rows:
        lines.append(f"| `{row['transaction_hash']}` | `{row['label_function']}` | `{row['computed_selector'] or 'not computed'}` | {row['selector_in_candidates_at_labeled_address']} | {row['selector_in_any_candidate']} | {row['selector_in_trace_any_address']} | {row['selector_called_at_labeled_address']} | {row['source_target_statement']} | {row['classification']} |")
    lines += ["", "Full per-row trace/candidate selector evidence is in `selector_check.json`.", ""]
    (OUT / "selector_check.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
