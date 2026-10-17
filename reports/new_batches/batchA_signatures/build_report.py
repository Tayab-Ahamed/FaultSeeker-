"""Build the Batch A full-signature audit from frozen local artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from eth_utils import keccak

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BATCH = ROOT / "reports/new_batches/batchA_candidates.json"
VALID = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json"
DIAGNOSIS = ROOT / "reports/new_batches/batchA_functiondiag/function_diagnosis.json"
RAW = ROOT / "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/raw"
POC = OUT / "poc_sources"

SOURCE_INFO = {
    "src/test/2021-09/DaoMaker_exp.sol": {
        "init": {
            "signature": "init(uint256,uint256[],uint256[],address)",
            "declaration_lines": list(range(19, 20)),
            "call_lines": list(range(42, 43)),
        },
    },
    "src/test/2022-06/XCarnival_exp.sol": {
        "pledgeAndBorrow": {
            "signature": "pledgeAndBorrow(address,uint256,uint256,address,uint256)",
            "declaration_lines": list(range(43, 50)),
            "call_lines": list(range(85, 86)),
        },
    },
    "src/test/2022-10/RabbyWallet_SwapRouter_exp.sol": {
        "swap": {
            "signature": "swap(address,uint256,address,uint256,address,address,bytes,uint256)",
            "declaration_lines": list(range(137, 147)),
            "call_lines": list(range(104, 114)),
        },
    },
    "src/test/2023-06/MIMSpell_exp.sol": {
        "swap": {
            "signature": "swap(address,address,address,uint256,uint256,bytes)",
            "declaration_lines": list(range(27, 35)),
            "call_lines": list(range(103, 104)),
        },
    },
    "src/test/2024-09/Shezmu_exp.sol": {
        "mint": {
            "signature": "mint(address,uint256)",
            "declaration_lines": list(range(69, 70)),
            "call_lines": list(range(53, 54)),
        },
    },
}


def source_lines(path: str, numbers: list[int]) -> list[dict[str, object]]:
    lines = (POC / Path(path).name).read_text(encoding="utf-8").splitlines()
    return [{"line": number, "text": lines[number - 1]} for number in numbers]


def trace_inputs(value: object, path: str = "result") -> list[dict[str, object]]:
    if not isinstance(value, dict):
        return []
    found: list[dict[str, object]] = []
    input_value = value.get("input")
    if isinstance(input_value, str):
        found.append({"path": path, "input": input_value})
    calls = value.get("calls")
    if isinstance(calls, list):
        for index, child in enumerate(calls):
            found.extend(trace_inputs(child, f"{path}.calls[{index}]"))
    return found


def trace_file(tx_hash: str) -> Path:
    matches = sorted(RAW.glob(f"*_eth_{tx_hash.lower()}_attempt01.json"))
    if len(matches) != 1:
        raise AssertionError(f"expected one saved raw trace for {tx_hash}, found {matches}")
    return matches[0]


def main() -> int:
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    valid = json.loads(VALID.read_text(encoding="utf-8"))
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    labels = {str(row["transaction_hash"]).lower(): row for row in batch["rows"]}
    diagnosis_rows = {str(row["transaction_hash"]).lower(): row for row in diagnosis["rows"]}
    rows = []
    for record in valid["records"]:
        label = labels[str(record["transaction_hash"]).lower()]
        tx_hash = str(label["transaction_hash"]).lower()
        function_name = str(label["vulnerable_function"]).removesuffix("()")
        evidence = SOURCE_INFO[str(label["source_path"])][function_name]
        signature = str(evidence["signature"])
        selector = "0x" + keccak(text=signature)[:4].hex()
        diagnosis_row = diagnosis_rows[tx_hash]
        candidate_selectors = {
            str(value).lower()
            for value in diagnosis_row["candidate_selector_equal_to_label_selector"]["selectors_at_address"]
        }
        raw_trace = json.loads(trace_file(tx_hash).read_text(encoding="utf-8"))
        calls = trace_inputs(raw_trace.get("result"))
        trace_matches = [call for call in calls if str(call["input"]).lower().startswith(selector)]
        in_candidates = selector.lower() in candidate_selectors
        in_trace = bool(trace_matches)
        if in_candidates:
            classification = "in_candidates"
        elif in_trace:
            classification = "in_trace_only"
        else:
            classification = "absent"
        rows.append({
            "transaction_hash": label["transaction_hash"],
            "labeled_address": label["vulnerable_contract"],
            "source_file": label["source_path"],
            "source_url": label["source_poc_url"],
            "source_transaction_line_from_label": label["source_transaction_line"],
            "vulnerable_function_line_from_label": label["vulnerable_function_line"],
            "vulnerable_function_label": label["vulnerable_function"],
            "vulnerable_function_quote": label["vulnerable_function_quote"],
            "full_signature": signature,
            "signature_source": {
                "declaration_lines": source_lines(str(label["source_path"]), evidence["declaration_lines"]),
                "call_lines": source_lines(str(label["source_path"]), evidence["call_lines"]),
            },
            "computed_selector": selector,
            "candidate_selectors_at_labeled_address": sorted(candidate_selectors),
            "selector_in_candidates_at_labeled_address": in_candidates,
            "selector_in_trace_any_call_input_prefix": in_trace,
            "trace_matching_call_paths": [str(call["path"]) for call in trace_matches],
            "classification": classification,
        })
    needed = sorted({row["source_file"] for row in rows})
    counts = {
        "rows": len(rows),
        "resolved_full_signatures": sum(row["full_signature"] is not None for row in rows),
        "unresolved_signatures": sum(row["full_signature"] is None for row in rows),
        "in_candidates": sum(row["classification"] == "in_candidates" for row in rows),
        "in_trace_only": sum(row["classification"] == "in_trace_only" for row in rows),
        "absent": sum(row["classification"] == "absent" for row in rows),
    }
    result = {
        "label": "Batch A full argument-typed signature check",
        "network_calls_for_audit": False,
        "source_fetch_performed": True,
        "source_commit": "7363f76db51f0fea97f8e659b20ee8bdc5fbca25",
        "source_fetch_date_utc": "2026-10-17T17:26:14Z",
        "source_files": [row["source_file"] for row in rows[:0]],
        "rows": rows,
        "counts": counts,
        "evidence": [
            "reports/new_batches/batchA_candidates.json",
            "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/valid_set.json",
            "reports/new_batches/batchA_functiondiag/function_diagnosis.json",
            "reports/new_batches/batchA_mining/run_20261017T115038Z_b545d3e1e0/raw/",
        ],
        "scope": "source-backed signature and selector presence check only; no rescoring, fixes, or tuning",
    }
    result["source_files"] = [
        {
            "path": path,
            "url": f"https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/{path}",
        }
        for path in needed
    ]
    (OUT / "signature_check.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# Batch A full-signature and selector check",
        "",
        "**Source fetch was limited to the five user-authorized raw files. The audit itself used only local files; no RPC, rescoring, fixes, or tuning.**",
        "",
        "## Source availability",
        "",
        "All five requested files were fetched at commit `7363f76db51f0fea97f8e659b20ee8bdc5fbca25` on `2026-10-17T17:26:14Z` UTC:",
        "",
    ]
    lines += [f"- `{path}` — `https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/7363f76db51f0fea97f8e659b20ee8bdc5fbca25/{path}`" for path in needed]
    lines += ["", "## Counts", "", "| Count | Value |", "| --- | ---: |", f"| Batch A valid ETH rows | {len(rows)} |", f"| Resolved full argument-typed signatures | {counts['resolved_full_signatures']} |", f"| Unresolved signatures | {counts['unresolved_signatures']} |", f"| In candidates at labeled address | {counts['in_candidates']} |", f"| In trace only | {counts['in_trace_only']} |", f"| Absent | {counts['absent']} |", "", "## Per-row evidence", "", "| Transaction | Labeled address | PoC | Full signature | Selector | Declaration lines | Call lines | Candidates | Trace prefix | Classification |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        decl = ",".join(str(item["line"]) for item in row["signature_source"]["declaration_lines"])
        call = ",".join(str(item["line"]) for item in row["signature_source"]["call_lines"])
        lines.append(f"| `{row['transaction_hash']}` | `{row['labeled_address']}` | `{Path(row['source_file']).name}` | `{row['full_signature']}` | `{row['computed_selector']}` | {decl} | {call} | {'yes' if row['selector_in_candidates_at_labeled_address'] else 'no'} | {'yes' if row['selector_in_trace_any_call_input_prefix'] else 'no'} | `{row['classification']}` |")
    lines += ["", "The declaration and call line numbers above refer to the fetched PoC files. No types were inferred. Candidate presence comes from the saved candidate-selector evidence at the labeled address; trace presence means the selector matched the prefix of any saved trace call input.", ""]
    (OUT / "signature_check.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
