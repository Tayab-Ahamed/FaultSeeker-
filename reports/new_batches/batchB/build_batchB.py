"""Freeze Batch B phase-1 source-backed dataset without RPC, tracing, or scoring."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from eth_utils import keccak

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
POC = OUT / "poc_sources"
COMMIT = "7363f76db51f0fea97f8e659b20ee8bdc5fbca25"
FETCH_DATES = {
    "2026-10-17T17:49:02Z": {
        "0x0DEX_exp.sol": "src/test/2023-09/0x0DEX_exp.sol",
        "0xf340_exp.sol": "src/test/2025-08/0xf340_exp.sol",
        "Audius_exp.sol": "src/test/2022-07/Audius_exp.sol",
        "Bancor_exp.sol": "src/test/2020-06/Bancor_exp.sol",
        "CEXISWAP_exp.sol": "src/test/2023-09/CEXISWAP_exp.sol",
        "CompounderFinance_exp.sol": "src/test/2023-06/CompounderFinance_exp.sol",
        "Cream_exp.sol": "src/test/2021-08/Cream_exp.sol",
        "Curve_exp01.sol": "src/test/2023-07/Curve_exp01.sol",
        "Curve_exp02.sol": "src/test/2023-07/Curve_exp02.sol",
        "GoodDollar_exp.sol": "src/test/2023-12/GoodDollar_exp.sol",
        "HundredFinance_2_exp.sol": "src/test/2023-04/HundredFinance_2_exp.sol",
        "LiFi_exp.sol": "src/test/2022-03/LiFi_exp.sol",
        "LendfMe_exp.sol": "src/test/2020-04/LendfMe_exp.sol",
        "MEV_0xa247_exp.sol": "src/test/2023-11/MEV_0xa247_exp.sol",
        "NomadBridge_exp.sol": "src/test/2022-08/NomadBridge_exp.sol",
        "Orion_exp.sol": "src/test/2023-02/Orion_exp.sol",
        "OrbitChain_exp.sol": "src/test/2024-01/OrbitChain_exp.sol",
        "Pawnfi_exp.sol": "src/test/2023-06/Pawnfi_exp.sol",
        "PestoToken_exp.sol": "src/test/2024-09/PestoToken_exp.sol",
        "Popsicle_exp.sol": "src/test/2021-08/Popsicle_exp.sol",
        "SASHAToken_exp.sol": "src/test/2024-10/SASHAToken_exp.sol",
        "Sturdy_exp.sol": "src/test/2023-06/Sturdy_exp.sol",
        "Sushi_Router_exp.sol": "src/test/2023-04/Sushi_Router_exp.sol",
        "TeamFinance_exp.sol": "src/test/2022-10/TeamFinance_exp.sol",
        "UwuLend_First_exp.sol": "src/test/2024-06/UwuLend_First_exp.sol",
        "XBridge_exp.sol": "src/test/2024-04/XBridge_exp.sol",
    },
    "2026-10-17T17:53:09Z": {
        "Conic_exp.sol": "src/test/2023-07/Conic_exp.sol",
        "Sonne_exp.sol": "src/test/2024-05/Sonne_exp.sol",
        "WiseLending_exp.sol": "src/test/2023-10/WiseLending_exp.sol",
    },
}

SPECS = [
    {"path": "src/test/2020-04/LendfMe_exp.sol", "tx": "0xae7d664bdfcc54220df4f18d339005c6faf6e62c9ca79c56387bc0389274363b", "name": "Lendf.Me", "category": "Reentrancy", "date": "2020-04", "address": "0x0eee3e3828a45f7601d5f54bf49bb01d1a9df5ea", "address_lines": [24], "signature": "withdraw(address,uint256)", "source_signature_lines": [18], "call_lines": [69], "tx_lines": [12]},
    {"path": "src/test/2020-06/Bancor_exp.sol", "tx": "0x4643b63dcbfc385b8ab8c86cbc46da18c2e43d277de3e5bc3b4516d3c0fdeb9f", "name": "Bancor", "category": "Access Control", "date": "2020-06", "address": "0x5f58058c0ec971492166763c8c22632b583f667f", "address_lines": [25], "signature": "safeTransferFrom(address,address,address,uint256)", "source_signature_lines": [20], "call_lines": [44, 45, 46, 47, 48, 49], "tx_lines": [16]},
    {"path": "src/test/2021-08/Popsicle_exp.sol", "tx": "0xcd7dae143a4c0223349c16237ce4cd7696b1638d116a72755231ede872ab70fc", "name": "Popsicle Finance", "category": "Reentrancy / Flash Loan", "date": "2021-08", "address": "0xc4ff55a4329f84f9bf0f5619998ab570481ebb48", "address_lines": [10], "signature": "collectFees(uint256,uint256)", "source_signature_lines": [40], "call_lines": [251], "tx_lines": [11]},
    {"path": "src/test/2022-07/Audius_exp.sol", "tx": "0x4227bca8ed4b8915c7eec0e14ad3748a88c4371d4176e716e8007249b9980dc9", "name": "Audius governance takeover", "category": "Governance Attack", "date": "2022-07", "address": "0x4deca517d6817b6510798b7328f2314d3003abac", "address_lines": [37], "signature": "evaluateProposalOutcome(uint256)", "source_signature_lines": [67, 68, 69], "call_lines": [166], "tx_lines": [12]},
    {"path": "src/test/2022-08/NomadBridge_exp.sol", "tx": "0xa5fe9d044e4f3e5aa5bc4c0709333cd2190cba0f4e7f16bcf73f49f83e4a5460", "name": "Nomad Bridge", "category": "Bridge Exploit", "date": "2022-08", "address": "0x5d94309e5a0090b165fa4181519701637b6daeba", "address_lines": [17, 32], "signature": "process(bytes)", "source_signature_lines": [87, 88, 89], "call_lines": [79], "tx_lines": [12]},
    {"path": "src/test/2023-04/Sushi_Router_exp.sol", "tx": "0x04b166e7b4ab5105a8e9c85f08f6346de1c66368687215b0e0b58d6e5002bc32", "name": "Sushi RouteProcessor2", "category": "DEX / Arbitrary Call", "date": "2023-04", "address": "0x044b75f554b886a065b9567891e45c79542d7357", "address_lines": [47], "signature": "processRoute(address,uint256,address,uint256,address,bytes)", "source_signature_lines": [27, 28, 29, 30, 31, 32, 33, 34], "call_lines": [69, 70, 71, 72, 73, 74, 75, 76], "tx_lines": [12]},
    {"path": "src/test/2023-06/Sturdy_exp.sol", "tx": "0xeb87ebc0a18aca7d2a9ffcabf61aa69c9e8d3c6efade9e2303f8857717fb9eb7", "name": "Sturdy Finance", "category": "Lending / Oracle Manipulation", "date": "2023-06", "address": "0x9f72dc67cec672bb99e3d02cbea0a21536a2b657", "address_lines": [10, 100], "signature": "borrow(address,uint256,uint256,uint16,address)", "source_signature_lines": [32, 33, 34, 35, 36, 37, 38], "call_lines": [255], "tx_lines": [11]},
    {"path": "src/test/2023-06/CompounderFinance_exp.sol", "tx": "0xcff84cc137c92e427f720ca1f2b36fbad793f34ec5117eed127060686e6797b1", "name": "Compounder Finance", "category": "Price Manipulation / Flash Loan", "date": "2023-06", "address": "0xaf274e912243b19b882f02d731dacd7cd13072d0", "address_lines": [10, 62], "signature": "deposit()", "source_signature_lines": [47], "call_lines": [110], "tx_lines": [11]},
    {"path": "src/test/2023-07/Curve_exp01.sol", "tx": "0xa84aa065ce61dbb1eb50ab6ae67fc31a9da50dd2c74eefd561661bfce2f1620c", "name": "Curve Vyper reentrancy 1", "category": "Reentrancy", "date": "2023-07", "address": "0x6326debbaa15bcfe603d831e7d75f4fc10d9b43e", "address_lines": [10], "signature": "remove_liquidity(uint256,uint256[2])", "source_signature_lines": [25], "call_lines": [71], "tx_lines": [11]},
    {"path": "src/test/2023-07/Curve_exp02.sol", "tx": "0x2e7dc8b2fb7e25fd00ed9565dcc0ad4546363171d5e00f196d48103983ae477c", "name": "Curve Vyper reentrancy 2", "category": "Reentrancy", "date": "2023-07", "address": "0x8301ae4fc9c624d1d396cbdaa1ed877821d7c511", "address_lines": [10, 44], "signature": "remove_liquidity(uint256,uint256[2],bool)", "source_signature_lines": [35], "call_lines": [87], "tx_lines": [11]},
    {"path": "src/test/2023-09/0x0DEX_exp.sol", "tx": "0x00b375f8e90fc54c1345b33c686977ebec26877e2c8cac165429927a6c9bdbec", "name": "0x0 Privacy DEX", "category": "DEX / Flash Loan", "date": "2023-09", "address": "0x29d2bcf0d70f95ce16697e645e2b76d218d66109", "address_lines": [10, 65], "signature": "swapOnWithdrawal(address,address,uint256,uint256,uint256,(uint256,uint256,uint256,uint256[2],uint256[],uint8))", "source_signature_lines": [48, 49, 50, 51, 52, 53, 54, 55], "call_lines": [135], "tx_lines": [11]},
    {"path": "src/test/2023-09/CEXISWAP_exp.sol", "tx": "0xede72a74d8398875b42d92c550539d72c830d3c3271a7641ee1843dc105de59e", "name": "CEXISWAP", "category": "Delegatecall Abuse / Access Control", "date": "2023-09", "address": "0xb8a5890d53df78dee6182a6c0968696e827e3305", "address_lines": [10, 30], "signature": "initialize(string,address,address,address,address,address)", "source_signature_lines": [17, 18, 19, 20, 21, 22, 23, 24], "call_lines": [58], "tx_lines": [11]},
    {"path": "src/test/2023-12/GoodDollar_exp.sol", "tx": "0x726459a46839c915ee2fb3d8de7f986e3c7391c605b7a622112161a84c7384d0", "name": "GoodDollar", "category": "Reentrancy / Business Logic", "date": "2023-12", "address": "0x0c6c80d2061afa35e160f3799411d83bdeea0a5a", "address_lines": [10, 146], "signature": "collectInterest(address[],bool)", "source_signature_lines": [28], "call_lines": [155], "tx_lines": [11]},
    {"path": "src/test/2024-01/OrbitChain_exp.sol", "tx": "0xe0bada18fdc56dec125c31b1636490f85ba66016318060a066ed7050ff7271f9", "name": "Orbit Chain", "category": "Bridge Exploit", "date": "2024-01", "address": "0x1bf68a9d1eaee7826b3593c20a0ca93293cb489a", "address_lines": [9, 35], "signature": "withdraw(address,string,bytes,address,address,bytes32[],uint256[],bytes,uint8[],bytes32[],bytes32[])", "source_signature_lines": list(range(16, 29)), "call_lines": list(range(95, 108)), "tx_lines": [10]},
    {"path": "src/test/2024-04/XBridge_exp.sol", "tx": "0x903d88a92cbc0165a7f662305ac1bff97430dbcccaa0fe71e101e18aa9109c92", "name": "XBridge", "category": "Bridge Exploit", "date": "2024-04", "address": "0x354cca2f55dde182d36fe34d673430e226a3cb8c", "address_lines": [9], "signature": "withdrawTokens(address,address,uint256)", "source_signature_lines": [27], "call_lines": [48], "tx_lines": [11]},
    {"path": "src/test/2023-07/Conic_exp.sol", "tx": "0x8b74995d1d61d3d7547575649136b8765acb22882960f0636941c44ec7bbe146", "name": "Conic Finance", "category": "Reentrancy / Oracle Manipulation", "date": "2023-07", "address": "0xbb787d6243a8d450659e09ea6fd82f1c859691e9", "address_lines": [10, 64], "signature": "handleDepeggedCurvePool(address)", "source_signature_lines": [21, 22, 23], "call_lines": [247], "tx_lines": [11]},
    {"path": "src/test/2024-10/SASHAToken_exp.sol", "tx": "0xd9fdc7d03eec28fc2453c5fa68eff82d4c297f436a6a5470c54ca3aecd2db17e", "name": "SASHA token", "category": "Token / Price Manipulation", "date": "2024-10", "address": "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", "address_lines": [19], "signature": "exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))", "source_signature_lines": [130, 131, 132], "call_lines": [100], "tx_lines": [10]},
    {"path": "src/test/2025-08/0xf340_exp.sol", "tx": "0x103b4550a1a2bdb73e3cb5ea484880cd8bed7e4842ecdd18ed81bf67ed19e03c", "name": "0xf340", "category": "Access Control", "date": "2025-08", "address": "0xf340bd3eb3e82994cff5b8c3493245edbce63436", "address_lines": [10, 26], "signature": "initVRF(address,address)", "source_signature_lines": [67, 68], "call_lines": [39], "tx_lines": [11]},
    {"path": "src/test/2022-03/LiFi_exp.sol", "tx": "0x1438ff9dd1cf9c70002c3b3cbec9c4c1b3f9eb02e29bcac90289ab3ba360e605", "name": "Li.Fi", "category": "Bridge Exploit / Arbitrary Call", "date": "2022-03", "address": "0x5a9fd7c39a6c488e715437d7b1f3c823d5596ed1", "address_lines": [46], "signature": "swapAndStartBridgeTokensViaCBridge((bytes32,string,address,address,address,address,uint256,uint256),(address,address,address,address,uint256,bytes)[],(address,address,uint256,uint64,uint64,uint32))", "source_signature_lines": list(range(37, 42)), "call_lines": [409], "tx_lines": [64]},
    {"path": "src/test/2023-10/WiseLending_exp.sol", "tx": "0x7ac4a98599596adbf12fffa2bd23e2a2d2ac7e8989b6ea043fcc412a29126555", "name": "Wise Lending", "category": "Lending / Inflation Attack", "date": "2023-10", "address": "0x84524baa1951247b3a2617a843e6ece915bb9674", "address_lines": [10, 50], "signature": "withdrawExactAmount(uint256,address,uint256)", "source_signature_lines": [35], "call_lines": [176], "tx_lines": [11]},
]

EXCLUSIONS = [
    {"file": "Cream_exp.sol", "incident": "Cream", "reason": "No explicit attack transaction hash; the candidate hash appears as a TOKENS_RECIPIENT_INTERFACE_HASH constant, not a PoC transaction URL."},
    {"file": "TeamFinance_exp.sol", "incident": "TeamFinance", "reason": "The target migrate/lock interface is imported from interface.sol; the fetched PoC does not provide a complete locally source-resolved target signature."},
    {"file": "HundredFinance_2_exp.sol", "incident": "Hundred Finance 2", "reason": "PoC setUp forks Optimism, not Ethereum mainnet."},
    {"file": "Pawnfi_exp.sol", "incident": "Pawnfi", "reason": "The vulnerable-contract comment address does not match the ApeStaking target addresses actually used by the PoC; contract-address match is ambiguous."},
    {"file": "PestoToken_exp.sol", "incident": "PestoToken", "reason": "Vulnerable Contract field is blank, so no source-backed vulnerable contract address can be recorded."},
    {"file": "MEV_0xa247_exp.sol", "incident": "MEV 0xa247", "reason": "The exploit uses low-level calls with raw selectors and internal helper functions; no complete externally callable typed target signature is provided."},
    {"file": "UwuLend_First_exp.sol", "incident": "UwuLend", "reason": "The vulnerable lending interface is imported from interface.sol and is not source-resolved in the fetched PoC; types are unresolved."},
    {"file": "Sonne_exp.sol", "incident": "Sonne", "reason": "PoC setUp forks Optimism, not Ethereum mainnet."},
    {"file": "Orion_exp.sol", "incident": "Orion Protocol", "reason": "The source transaction is already present in the excluded 110 benchmark rows."},
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def line_quotes(path: str, numbers: list[int]) -> list[dict[str, object]]:
    lines = (POC / Path(path).name).read_text(encoding="utf-8").splitlines()
    return [{"line": number, "text": lines[number - 1]} for number in numbers]


def canonical_hash(payload: dict) -> str:
    body = dict(payload)
    body.pop("artifact_sha256", None)
    encoded = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    # Exclusion sets: the 115 original ground-truth JSONs, the 110 provider-pinned
    # benchmark raw rows, and Batch A. All reads are local.
    gt_hashes = {p.stem.lower() for p in (ROOT / "benchmark/original_faultseeker/ground_truth").glob("*.json")}
    benchmark_raw_all = {p.stem.lower() for p in (ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw").glob("*.json")}
    benchmark_manifest = read_json(ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/manifest.json")
    benchmark_failed = {str(item["txn_hash"]).lower() for item in benchmark_manifest["final_reporting"]["failure_details"]}
    benchmark_raw = benchmark_raw_all - benchmark_failed
    batch_a = {str(row["transaction_hash"]).lower() for row in read_json(ROOT / "reports/new_batches/batchA_candidates.json")["rows"]}
    excluded_hashes = gt_hashes | benchmark_raw | batch_a
    assert len(gt_hashes) == 115
    assert len(benchmark_raw_all) == 115
    assert len(benchmark_failed) == 5
    assert len(benchmark_raw) == 110

    rows = []
    for spec in SPECS:
        tx = spec["tx"].lower()
        source_path = POC / Path(spec["path"]).name
        text = source_path.read_text(encoding="utf-8").lower()
        tx_quotes = line_quotes(spec["path"], spec["tx_lines"])
        address_quotes = line_quotes(spec["path"], spec["address_lines"])
        signature_quotes = line_quotes(spec["path"], spec["source_signature_lines"])
        call_quotes = line_quotes(spec["path"], spec["call_lines"])
        assert tx in "\n".join(item["text"].lower() for item in tx_quotes), spec["path"]
        assert spec["address"].lower() in "\n".join(item["text"].lower() for item in address_quotes), spec["path"]
        assert tx not in excluded_hashes, f"selected transaction intersects exclusions: {tx}"
        selector = "0x" + keccak(text=spec["signature"])[:4].hex()
        rows.append({
            "chain": "eth",
            "incident_name": spec["name"],
            "incident_date": spec["date"],
            "transaction_hash": tx,
            "source_path": spec["path"],
            "source_url": f"https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/{COMMIT}/{spec['path']}",
            "source_commit": COMMIT,
            "vulnerable_contract_address": spec["address"],
            "full_signature": spec["signature"],
            "selector": selector,
            "vulnerability_category": spec["category"],
            "source_evidence": {
                "transaction_lines": tx_quotes,
                "contract_address_lines": address_quotes,
                "signature_declaration_lines": signature_quotes,
                "poc_call_lines": call_quotes,
            },
            "source_match_checks": {
                "transaction_hash_present_in_source_lines": True,
                "contract_address_present_in_source_lines": True,
                "target_externally_callable": True,
                "signature_types_source_resolved": True,
            },
        })

    assert len(rows) == 20
    assert len({row["transaction_hash"] for row in rows}) == 20
    assert len({row["incident_name"] for row in rows}) == 20
    assert not ({row["transaction_hash"] for row in rows} & excluded_hashes)

    payload = {
        "batch_id": "batchB",
        "status": "frozen",
        "phase": "phase_1_dataset_and_protocol_only",
        "chain": "eth",
        "source_repository": "https://github.com/SunWeb3Sec/DeFiHackLabs",
        "source_commit": COMMIT,
        "selection_policy": "Incident diversity and source evidence only; not selected by ranker behaviour.",
        "exclusion_policy": {
            "ground_truth_json_count": 115,
            "benchmark_row_count": 110,
            "batch_a_row_count": 23,
            "selected_tx_intersections": 0,
            "one_transaction_per_incident": True,
        },
        "row_count": len(rows),
        "rows": rows,
    }
    payload["artifact_sha256"] = canonical_hash(payload)
    (OUT / "batchB_candidates.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    manifest = []
    for fetch_date, files in FETCH_DATES.items():
        for filename, path in sorted(files.items()):
            content = (POC / filename).read_bytes()
            manifest.append({
                "file": filename,
                "source_path": path,
                "source_url": f"https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/{COMMIT}/{path}",
                "commit": COMMIT,
                "fetched_at_utc": fetch_date,
                "network_requests": 1,
                "content_sha256": hashlib.sha256(content).hexdigest(),
            })
    assert len(manifest) == 29
    (OUT / "source_manifest.json").write_text(json.dumps({"repository": "https://github.com/SunWeb3Sec/DeFiHackLabs", "commit": COMMIT, "files": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    category_counts = Counter(row["vulnerability_category"] for row in rows)
    year_counts = Counter(row["incident_date"] for row in rows)
    report = [
        "# Batch B phase 1 report",
        "",
        "**Frozen: 20 distinct Ethereum-mainnet incidents, DeFiHackLabs-sourced.**",
        "",
        "No RPC, node tracing, scoring, ranker invocation, or result-file change was performed. Selection used source-backed incident diversity only, not ranker behaviour.",
        "",
        f"Pinned source commit: `{COMMIT}`",
        f"Frozen canonical JSON SHA-256: `{payload['artifact_sha256']}`",
        "",
        "## Counts by vulnerability category",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    report += [f"| {key} | {category_counts[key]} |" for key in sorted(category_counts)]
    report += ["", "## Counts by incident month", "", "| Month | Count |", "| --- | ---: |"]
    report += [f"| {key} | {year_counts[key]} |" for key in sorted(year_counts)]
    report += ["", "## Exclusions", "", "| File | Incident | Reason |", "| --- | --- | --- |"]
    report += [f"| `{item['file']}` | {item['incident']} | {item['reason']} |" for item in EXCLUSIONS]
    report += [
        "",
        "The exclusion scan used 115 local ground-truth JSON hashes, 110 local provider-pinned benchmark rows, and all Batch A transaction hashes. No frozen Batch B transaction intersected those sets.",
        "",
        "## What tracing needs later",
        "",
        "- A node/provider with full Ethereum mainnet execution traces for each frozen transaction and receipt history.",
        "- Receipt transaction hash, transaction block number, and receipt block number for verification; pending or mismatched records are excluded.",
        "- The provider key must remain outside chat and outside the repository. Phase 1 does not request or use it.",
        "- The future run follows `PROTOCOL.md`: one producer-era replay at commit `1b1c739`, one scoring run, address+selector primary, address-only and selector-only sensitivity, R@1/3/5, and no Batch B tuning or partial-result peeking.",
        "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8", newline="\n")
    (OUT / "FREEZE.md").write_text(
        "# Batch B freeze\n\n"
        "`batchB_candidates.json` is frozen for phase 1.\n\n"
        f"Canonicalization: `json.dumps(payload_without_artifact_sha256, indent=2, sort_keys=True) + newline`, UTF-8.\n\n"
        f"SHA-256: `{payload['artifact_sha256']}`\n\n"
        f"Rows: `{len(rows)}`\n\n"
        "No edits are permitted after this freeze.\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
