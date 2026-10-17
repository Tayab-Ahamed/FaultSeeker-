"""Offline post-hoc selector alignment over saved Batch A candidate lists."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SIGNATURES = ROOT / "reports/new_batches/batchA_signatures/signature_check.json"
SAVED_LISTS = ROOT / "reports/new_batches/batchA_ranker_measurement_20261017.json"
DRPC_SUMMARY = ROOT / "reports/new_batches/batchA_adapterfix4/producer_batchA_measurement_drpc_final.json"
DIAGNOSIS = ROOT / "reports/new_batches/batchA_functiondiag/function_diagnosis.json"


def first_rank(rows: list[dict], predicate) -> int | None:
    for row in rows:
        if predicate(row):
            return int(row["rank"])
    return None


def metrics(ranks: list[int | None]) -> dict[str, dict[str, int | float]]:
    result = {}
    for k in (1, 3, 5):
        hits = sum(rank is not None and rank <= k for rank in ranks)
        result[f"R@{k}"] = {"hits": hits, "n": len(ranks), "recall": hits / len(ranks)}
    return result


def main() -> int:
    signatures = json.loads(SIGNATURES.read_text(encoding="utf-8"))
    saved_lists = json.loads(SAVED_LISTS.read_text(encoding="utf-8"))
    drpc = json.loads(DRPC_SUMMARY.read_text(encoding="utf-8"))
    diagnosis = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))

    signature_rows = {row["transaction_hash"].lower(): row for row in signatures["rows"]}
    saved_rows = {row["transaction_hash"].lower(): row for row in saved_lists["rows"]}
    drpc_rows = {row["transaction_hash"].lower(): row for row in drpc["candidate_counts"]["rows"]}
    diagnosis_rows = {row["transaction_hash"].lower(): row for row in diagnosis["rows"]}
    assert len(signature_rows) == len(saved_rows) == len(drpc_rows) == len(diagnosis_rows) == 23

    rows = []
    for tx in signature_rows:
        signature = signature_rows[tx]
        saved = saved_rows[tx]
        producer = drpc_rows[tx]
        diag = diagnosis_rows[tx]
        address = signature["labeled_address"].lower()
        selector = signature["computed_selector"].lower()
        predictions = saved["predictions"]

        address_only_rank = first_rank(
            predictions,
            lambda prediction: str(prediction.get("code_address") or prediction.get("address") or "").lower() == address,
        )
        address_selector_rank = first_rank(
            predictions,
            lambda prediction: (
                str(prediction.get("code_address") or prediction.get("address") or "").lower() == address
                and str(prediction.get("selector") or prediction.get("function") or "").lower() == selector
            ),
        )

        # The drpc_final summary is authoritative for its candidate count and
        # address-only rank. The saved full-list artifact is used only; no
        # ranker invocation occurs here.
        assert address_only_rank == producer["address_only_rank"]
        assert int(saved["prediction_count"]) == int(diag["candidate_count"]) or tx == "0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d"
        assert int(diag["candidate_count"]) == int(producer["candidate_count"]) or tx == "0xabfcfaf3620bbb2d41a3ffea6e31e93b9b5f61c061b9cfc5a53c74ebe890294d"

        diag_match = next(
            (item for item in diag["top5_at_labeled_address"] if item["selector"].lower() == selector),
            None,
        )
        if address_selector_rank is None:
            assert diag_match is None
        else:
            assert diag_match is not None
            assert int(diag_match["rank"]) == address_selector_rank

        rows.append({
            "transaction_hash": signature["transaction_hash"],
            "transaction_hash_prefix": signature["transaction_hash"][:10],
            "labeled_address": signature["labeled_address"],
            "full_signature": signature["full_signature"],
            "selector": selector,
            "candidate_count": int(producer["candidate_count"]),
            "address_only_rank": producer["address_only_rank"],
            "address_selector_rank": address_selector_rank,
            "first_labeled_address_selector_match_rank": address_selector_rank,
            "matching_candidate": None if address_selector_rank is None else {
                "rank": address_selector_rank,
                "address": address,
                "selector": selector,
            },
            "selector_status": "absent" if address_selector_rank is None else "present",
        })

    address_selector_ranks = [row["address_selector_rank"] for row in rows]
    address_only_ranks = [row["address_only_rank"] for row in rows]
    result = {
        "label": "post-hoc label alignment, exploratory, N=23, ETH only, DeFiHackLabs-sourced",
        "alignment_key": "labeled vulnerable address + resolved full-signature keccak256 selector",
        "alignment_key_selection": "Chosen after seeing the name-matching zeros; exploratory and post-hoc, not a benchmark scoring change.",
        "network_calls": False,
        "ranker_invocations": 0,
        "source_candidate_lists": "reports/new_batches/batchA_ranker_measurement_20261017.json",
        "producer_replay_provenance": {
            "run_summary": "reports/new_batches/batchA_adapterfix4/producer_batchA_measurement_drpc_final.json",
            "raw_run_directory": "reports/new_batches/batchA_adapterfix4/rpc_drpc_final/eth/",
            "producer_commit": "1b1c7395771663622dd14b9731b4b8b471221960",
            "diagnostic_provenance": "reports/new_batches/batchA_functiondiag/function_diagnosis.json",
        },
        "counts": {
            "rows": len(rows),
            "resolved_full_signatures": sum(row["full_signature"] is not None for row in rows),
            "unresolved_full_signatures": sum(row["full_signature"] is None for row in rows),
            "selector_present": sum(row["address_selector_rank"] is not None for row in rows),
            "selector_absent": sum(row["address_selector_rank"] is None for row in rows),
        },
        "metrics": {
            "address_selector_primary": metrics(address_selector_ranks),
            "address_only_comparison": metrics(address_only_ranks),
        },
        "rows": rows,
        "caveats": [
            "This selector alignment is not the benchmark's name-based scoring rule.",
            "The address+selector key was chosen after seeing name-matching zeros.",
            "Two rows have the resolved selector absent from the saved candidate evidence and therefore have None ranks: DaoMaker init and XCarnival pledgeAndBorrow for 0xabfcfaf3....",
            "The sample is single-chain ETH only and small (N=23).",
            "Labels and full signatures were taken from the fetched DeFiHackLabs PoC source declarations and call lines recorded in batchA_signatures.",
            "The saved full-list artifact has 89 predictions for 0xabfcfaf3..., while the drpc_final summary records 88; this report uses the drpc_final candidate count, and that row's resolved selector is absent in both saved address-level evidence sets.",
        ],
        "evidence": [
            "reports/new_batches/batchA_signatures/signature_check.json",
            "reports/new_batches/batchA_ranker_measurement_20261017.json",
            "reports/new_batches/batchA_adapterfix4/producer_batchA_measurement_drpc_final.json",
            "reports/new_batches/batchA_functiondiag/function_diagnosis.json",
        ],
    }
    (OUT / "selector_alignment.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    lines = [
        "# Batch A selector alignment",
        "",
        "**post-hoc label alignment, exploratory, N=23, ETH only, DeFiHackLabs-sourced**",
        "",
        "No RPC, network, ranker invocation, rescoring, tuning, or production-code change was performed. The saved producer-era candidate evidence was reused from the dRPC final replay artifacts.",
        "",
        "The alignment key was chosen after seeing the name-matching zeros. It is the labeled vulnerable address plus the keccak256 selector of the resolved full signature.",
        "",
        "## Metrics",
        "",
        "| Alignment | R@1 | R@3 | R@5 | N |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, key in (("Address + selector (primary)", "address_selector_primary"), ("Address-only (comparison)", "address_only_comparison")):
        metric = result["metrics"][key]
        lines.append("| " + label + " | " + " | ".join(f"{metric[f'R@{k}']['hits']}/{metric[f'R@{k}']['n']} ({metric[f'R@{k}']['recall']:.6f})" for k in (1, 3, 5)) + " | 23 |")
    lines += [
        "",
        "## Per-row ranks",
        "",
        "`address+selector rank` is the global rank of the first saved candidate matching both the labeled address and resolved selector. `address-only rank` is the first saved candidate matching only the labeled address.",
        "",
        "| Tx prefix | Address+selector rank | Address-only rank | Candidate count | Selector |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(f"| `{row['transaction_hash_prefix']}` | {row['address_selector_rank']} | {row['address_only_rank']} | {row['candidate_count']} | `{row['selector']}` |")
    lines += [
        "",
        "## Caveats",
        "",
        "- Selector alignment is exploratory and differs from the benchmark's name-based scoring.",
        "- The address+selector alignment key was selected after the name-matching results were zero.",
        "- Two rows have absent selectors and therefore `None` address+selector ranks.",
        "- This is a single-chain ETH-only sample with N=23.",
        "- Labels were taken from the DeFiHackLabs PoC source declarations and call lines; no types were guessed.",
        "- The saved full-list artifact records 89 candidates for `0xabfcfaf3...`, while the drpc_final summary records 88; the table uses the drpc_final count and the selector is absent in both saved address-level evidence sets.",
        "",
    ]
    (OUT / "selector_alignment.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
