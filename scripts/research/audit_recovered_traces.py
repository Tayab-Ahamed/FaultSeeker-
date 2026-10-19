"""Audit locally retained RPC traces against original ground-truth identities.

This is an evidence-recovery audit, not a new localization score.  It reads
only captured, redacted callTracer artifacts from the bounded external run and
the imported original ground truth.  It records observed target addresses and
raw call selectors without inferring a function name from an untyped label.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "reports/external_runs/phase2/20261017T011500Z/drpc"
MANIFEST = RUN_DIR / "manifest.json"
ORIGINAL_GT = ROOT / "benchmark/original_faultseeker/ground_truth"
OUTPUT_JSON = ROOT / "reports/reconciliation/recovered_trace_audit.json"
OUTPUT_MD = ROOT / "reports/reconciliation/RECOVERED_TRACE_AUDIT.md"

# Public typed-signature evidence recovered after the callTracer audit.  The
# first three records are exact-match verified contract pages on Etherscan;
# the Euler proxy's implementation is not source-verified at the target
# address, so its selector is recorded from OpenChain's public signature
# database and is not treated as verified source.
TYPED_SIGNATURES = {
    ("eth", "0xb40b6608b2743e691c9b54ddbdee7bf03cd79f1c", "cacheassetprice"): {
        "signature": "cacheAssetPrice()",
        "selector": "0xd341ea79",
        "provenance": "etherscan_verified_exact_match",
        "source_url": "https://etherscan.io/address/0xb40b6608b2743e691c9b54ddbdee7bf03cd79f1c#code",
    },
    ("eth", "0xe8b3bc58774857732c6c1147bfc9b9e5fb6f427c", "latestanswer"): {
        "signature": "latestAnswer()",
        "selector": "0x50d25bcd",
        "provenance": "etherscan_verified_exact_match",
        "source_url": "https://etherscan.io/address/0xe8b3bc58774857732c6c1147bfc9b9e5fb6f427c#code",
    },
    ("eth", "0x420a50a62b17c18b36c64478784536ba980feac8", "doswapthroughorionpool"): {
        "signature": "doSwapThroughOrionPool(address,address,(uint112,uint112,address,bool,bool,bool,bool,bool,address,address[]))",
        "selector": "0xd5f724f3",
        "provenance": "etherscan_verified_exact_match",
        "source_url": "https://etherscan.io/address/0x420a50a62b17c18b36c64478784536ba980feac8#code",
    },
    ("eth", "0xe025e3ca2be02316033184551d4d3aa22024d9dc", "donatetoreserves"): {
        "signature": "donateToReserves(uint256,uint256)",
        "selector": "0x36f022aa",
        "provenance": "openchain_signature_database_has_verified_contract",
        "source_url": "https://api.openchain.xyz/signature-database/v1/lookup?function=0x36f022aa",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _chain(value: Any) -> str:
    return {
        "ethereum": "eth",
        "mainnet": "eth",
        "bnbchain": "bsc",
        "binance": "bsc",
        "binancesmartchain": "bsc",
    }.get(_norm(value), _norm(value))


def stable_id(chain: Any, txn_hash: Any) -> str:
    return f"{_chain(chain)}:{_norm(txn_hash)}"


def _iter_calls(node: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("calls") or []:
        yield from _iter_calls(child)


def observed_calls(raw: dict[str, Any]) -> list[dict[str, str]]:
    """Return unique observed ``to``/raw 4-byte input pairs in call order."""
    trace = None
    for request in raw.get("requests") or []:
        if request.get("method") != "debug_traceTransaction":
            continue
        body = (request.get("response") or {}).get("body") or {}
        if isinstance(body, dict) and isinstance(body.get("result"), dict):
            trace = body["result"]
            break
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for node in _iter_calls(trace):
        address = _norm(node.get("to"))
        input_data = _norm(node.get("input"))
        selector = input_data[:10] if input_data.startswith("0x") and len(input_data) >= 10 else ""
        if not address or not selector or (address, selector) in seen:
            continue
        seen.add((address, selector))
        result.append({"address": address, "selector": selector})
    return result


def _ground_truth(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    hashes = raw.get("transaction_hash") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    chain = _chain(raw.get("platform") or raw.get("chain"))
    addresses: set[str] = set()
    function_labels: list[dict[str, str]] = []
    for key in (raw.get("location") or {}):
        parts = str(key).split("#")
        if parts and parts[0].strip():
            addresses.add(_norm(parts[0]))
    for key, values in (raw.get("location") or {}).items():
        parts = str(key).split("#")
        address = _norm(parts[0]) if parts else ""
        for entry in values or []:
            entry_parts = str(entry).split("#")
            if len(entry_parts) < 3:
                continue
            member = str(entry_parts[-1]).strip()
            if ":" in member and member.split(":", 1)[0].strip().isdigit():
                continue
            if address and member:
                function_labels.append({"address": address, "label": member})
    return {
        "stable_id": stable_id(chain, hashes[0] if hashes else path.stem),
        "chain": chain,
        "transaction_hash": _norm(hashes[0] if hashes else path.stem),
        "addresses": sorted(addresses),
        "function_labels": function_labels,
    }


def _ground_truth_index() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(ORIGINAL_GT.glob("*.json")):
        row = _ground_truth(path)
        result.setdefault(row["stable_id"], row)
    return result


def _captured_manifest_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for chain, group in (manifest.get("chains") or {}).items():
        for attempt in group.get("attempts") or []:
            if attempt.get("status") != "CAPTURED":
                continue
            tx = _norm(attempt.get("transaction_hash"))
            rows.append({"chain": chain, "transaction_hash": tx})
    return rows


def _raw_path(chain: str, txn_hash: str) -> Path:
    return RUN_DIR / "raw" / chain / f"{txn_hash}.attempt1.json"


def run() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ground_truth = _ground_truth_index()
    captured = _captured_manifest_rows(manifest)
    rows: list[dict[str, Any]] = []
    for item in captured:
        tx = item["transaction_hash"]
        path = _raw_path(item["chain"], tx)
        raw = json.loads(path.read_text(encoding="utf-8"))
        expected = ground_truth.get(stable_id(item["chain"], tx))
        calls = observed_calls(raw)
        addresses = sorted({call["address"] for call in calls})
        target_addresses = expected["addresses"] if expected else []
        target_hits = [call for call in calls if call["address"] in target_addresses]
        typed_evidence = []
        for label in (expected["function_labels"] if expected else []):
            evidence = TYPED_SIGNATURES.get((item["chain"], label["address"], _norm(label["label"])))
            if evidence:
                typed_evidence.append({
                    **evidence,
                    "ground_truth_label": label["label"],
                    "selector_observed": evidence["selector"] in {call["selector"] for call in target_hits},
                })
        tx_result = next(
            ((request.get("response") or {}).get("body") or {}).get("result")
            for request in raw.get("requests") or []
            if request.get("method") == "eth_getTransactionByHash"
        )
        rows.append({
            "stable_id": stable_id(item["chain"], tx),
            "chain": item["chain"],
            "transaction_hash": tx,
            "raw_path": path.relative_to(ROOT).as_posix(),
            "raw_sha256": _sha256(path),
            "observed_chain_id": raw.get("observed_chain_id"),
            "transaction_result_hash_matches": _norm((tx_result or {}).get("hash")) == tx,
            "observed_call_count": len(calls),
            "observed_address_count": len(addresses),
            "ground_truth_available": expected is not None,
            "ground_truth_target_addresses": target_addresses,
            "ground_truth_function_labels": expected["function_labels"] if expected else [],
            "target_address_observed": bool(target_hits),
            "target_address_call_count": len(target_hits),
            "target_address_observed_selectors": sorted({call["selector"] for call in target_hits}),
            "typed_function_signature_evidence": typed_evidence,
            "exact_function_identity_status": (
                "ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE"
                if any(item["selector_observed"] for item in typed_evidence)
                else "TYPED_SIGNATURE_FOUND_BUT_SELECTOR_NOT_OBSERVED"
                if typed_evidence
                else "NOT_IDENTIFIABLE_FROM_UNTYPED_LABEL" if expected and expected["function_labels"] else "NO_IMPORTED_GROUND_TRUTH"
            ),
        })

    failed = []
    for chain, group in (manifest.get("chains") or {}).items():
        for attempt in group.get("attempts") or []:
            if attempt.get("status") != "CAPTURED":
                failed.append({"chain": chain, **attempt})
    by_status = Counter("captured" for _ in rows)
    summary = {
        "captured_rows": len(rows),
        "failed_attempts": len(failed),
        "captured_rows_with_original_ground_truth": sum(row["ground_truth_available"] for row in rows),
        "captured_rows_with_observed_target_address": sum(row["target_address_observed"] for row in rows),
        "captured_rows_with_exact_function_identity": sum(
            row["exact_function_identity_status"] == "ESTABLISHED_BY_TYPED_SIGNATURE_AND_TRACE" for row in rows
        ),
        "captured_rows_with_transaction_hash_match": sum(row["transaction_result_hash_matches"] for row in rows),
        "target_address_observation_is_not_function_reproduction": True,
        "provider": "dRPC",
        "run_manifest_sha256": _sha256(MANIFEST),
        "status_counts": dict(by_status),
    }
    typed_evidence_catalog = [
        {"chain": key[0], "address": key[1], "label": key[2], **value}
        for key, value in sorted(TYPED_SIGNATURES.items())
    ]
    result = {
        "schema_version": 1,
        "scope": "Bounded, previously captured dRPC callTracer artifacts; no new RPC requests; no ranking run.",
        "source_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "summary": summary,
        "rows": rows,
        "typed_signature_evidence": typed_evidence_catalog,
        "failed_attempts": failed,
        "blocker": "Raw callTracer proves observed target-address calls and raw selectors where present. Typed public signatures establish four captured function identities, but exact identities for the remaining rows and paper scorer reproduction remain blocked.",
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Recovered original-benchmark trace audit",
        "",
        "This report audits previously captured, redacted dRPC callTracer responses. It does not make new RPC requests, rerun ranking, or infer function names from untyped labels.",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Captured rows | {summary['captured_rows']} |",
        f"| Failed attempts | {summary['failed_attempts']} |",
        f"| Captured rows with imported original ground truth | {summary['captured_rows_with_original_ground_truth']} |",
        f"| Captured rows with observed target address | {summary['captured_rows_with_observed_target_address']} |",
        f"| Transaction hash checks passed | {summary['captured_rows_with_transaction_hash_match']} |",
        f"| Exact function identities established from typed public evidence plus trace | {summary['captured_rows_with_exact_function_identity']} |",
        "",
        "| Stable ID | Ground-truth address | Observed? | Observed selectors | Identity status |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        targets = ", ".join(row["ground_truth_target_addresses"]) or "n/a"
        selectors = ", ".join(row["target_address_observed_selectors"]) or "none"
        typed = ", ".join(
            f"{item['signature']}={item['selector']} ({item['provenance']})"
            for item in row["typed_function_signature_evidence"]
        ) or "none"
        lines.append(f"| `{row['stable_id']}` | `{targets}` | {str(row['target_address_observed']).lower()} | `{selectors}` | {row['exact_function_identity_status']} |")
        if typed:
            lines.append(f"| ↳ typed evidence |  |  |  | {typed} |")
    lines += [
        "",
        "For four captured original rows, a public typed-signature source now maps the imported label to an observed selector. This establishes the observed function identity for those rows only; it does not reproduce the original paper scorer or prove the remaining 111 identities.",
        "",
        f"Source manifest SHA-256: `{summary['run_manifest_sha256']}`",
    ]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
