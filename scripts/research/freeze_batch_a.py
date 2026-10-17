"""Freeze a source-labeled Batch A without touching RPC or trace state.

The script intentionally consumes only the public DeFiHackLabs source archive and
the repository's existing ground-truth filenames. It records exact source lines
for the transaction, vulnerable contract, and vulnerable function evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


REPOSITORY = "SunWeb3Sec/DeFiHackLabs"
DEFAULT_REVISION = "7363f76db51f0fea97f8e659b20ee8bdc5fbca25"
DEFAULT_OUTPUT = Path("reports/new_batches/batchA_candidates.json")
SUPPORTED_CHAINS = ("eth", "base", "polygon", "bsc")
TX_RE = re.compile(r"0x[a-fA-F0-9]{64}")
ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")


def spec(
    chain: str,
    path: str,
    function_name: str,
    function_pattern: str,
    vulnerability_type: str,
    *,
    contract_pattern: str = r"vulnerable\s*contract|victim\s*contract|vulnerablecontract",
    bare_tx_block: bool = False,
) -> dict:
    return {
        "chain": chain,
        "path": path,
        "function_name": function_name,
        "function_pattern": function_pattern,
        "vulnerability_type": vulnerability_type,
        "contract_pattern": contract_pattern,
        "bare_tx_block": bare_tx_block,
    }


SPECS = [
    # ETH: several transactions are explicitly listed for these PoCs.
    spec("eth", "src/test/2022-10/RabbyWallet_SwapRouter_exp.sol", "swap()", r"swap\(\).*vulnerability", "Arbitrary External Call", bare_tx_block=True),
    spec("eth", "src/test/2022-06/XCarnival_exp.sol", "pledgeAndBorrow()", r"pledgeAndBorrow\(\).*vulnerable", "Access Control"),
    spec("eth", "src/test/2023-06/MIMSpell_exp.sol", "swap()", r"vulnerable swap\(\) function", "Arbitrary External Call"),
    spec("eth", "src/test/2021-09/DaoMaker_exp.sol", "init()", r"left the `init` function unprotected", "Access Control", contract_pattern=r"0x6e70c88be1d5c2a4c0c8205764d01abe6a3d2e22.*emergencyExit"),
    spec("eth", "src/test/2024-09/Shezmu_exp.sol", "mint()", r"collateral token contract mint\(\) function", "Access Control"),

    # BSC: comments in the PoCs name the vulnerable function directly.
    spec("bsc", "src/test/2025-08/d3xai_exp.sol", "exchange()", r"proxy.*exchange\(\).*buy low", "Price Manipulation"),
    spec("bsc", "src/test/2025-08/Grizzifi_exp.sol", "_incrementUplineTeamCount()", r"root cause is, in the _incrementUplineTeamCount", "Access Control"),
    spec("bsc", "src/test/2022-10/ATK_exp.sol", "getPrice()", r"Root cause: getPrice\(\) function", "Oracle Manipulation"),
    spec("bsc", "src/test/2024-11/MFT_exp.sol", "MFT.transfer()", r"MFT\.transfer\(\) will burn token", "Token Accounting"),
    spec("bsc", "src/test/2022-10/BEGO_exp.sol", "mint()", r"vulnerability in the `mint\(\)` function", "Access Control"),
    spec("bsc", "src/test/2022-10/HEALTH_exp.sol", "_transfer()", r"vulnerability in the `_transfer\(\)` function|vulnerability in `_transfer\(\)` function", "Token Accounting"),
    spec("bsc", "src/test/2024-11/Ak1111_exp.sol", "mint()", r"mint AK1111 token for free", "Access Control"),
    spec("bsc", "src/test/2022-10/Carrot_exp.sol", "migrateStake()", r"access control to the migrateStake function", "Access Control"),
    spec("bsc", "src/test/2023-05/landNFT_exp.sol", "mint()", r"lack of permission control on mint", "Access Control"),
    spec("bsc", "src/test/2023-09/DEXRouter_exp.sol", "a()", r'call back "a" payable function', "Arbitrary External Call", contract_pattern=r"victim\s*contract"),

    # Base: keep the callback and swap PoCs that name the target function.
    spec("base", "src/test/2025-08/0x8d2e_exp.sol", "uniswapV3SwapCallback()", r"lacks access control in its uniswapV3SwapCallback function", "Access Control"),
    spec("base", "src/test/2024-12/CloberDEX_exp.sol", "mint()", r"function\s+mint\s*\(", "Access Control"),
    spec("base", "src/test/2024-05/TSURU_exp.sol", "swap()", r"function\s+swap\s*\(", "Price Manipulation"),

    # Polygon: the source summary and interface identify the exact callable.
    spec("polygon", "src/test/2023-03/Phoenix_exp.sol", "delegateCallSwap()", r"delegateCallSwap\(\) function lack of access control", "Access Control"),
    spec("polygon", "src/test/2023-05/LFI_exp.sol", "claimReward()", r"function\s+claimReward\s*\(", "Access Control"),
]


def read_ground_truth_hashes(root: Path) -> set[str]:
    return {path.stem.lower() for path in root.glob("0x" + "?" * 64 + ".json")}


def github_url(path: str, revision: str) -> str:
    return f"https://github.com/{REPOSITORY}/blob/{revision}/{path}"


def source_lines(archive: zipfile.ZipFile, path: str) -> list[str]:
    return archive.read(f"DeFiHackLabs-main/{path}").decode("utf-8", errors="replace").splitlines()


def find_line(lines: list[str], pattern: str) -> tuple[int, str] | None:
    compiled = re.compile(pattern, re.IGNORECASE)
    for number, line in enumerate(lines, start=1):
        if compiled.search(line):
            return number, line
    return None


def transaction_lines(lines: list[str], chain: str, bare_tx_block: bool) -> list[tuple[str, int, str]]:
    hosts = {
        "eth": ("etherscan.io/tx", "app.blocksec.com/explorer/tx/eth"),
        "base": ("basescan.org/tx", "app.blocksec.com/explorer/tx/base"),
        "polygon": ("polygonscan.com/tx", "phalcon.blocksec.com/tx/polygon"),
        "bsc": ("bscscan.com/tx", "phalcon.blocksec.com/tx/bsc"),
    }[chain]
    found: list[tuple[str, int, str]] = []
    in_bare_block = False
    for number, line in enumerate(lines, start=1):
        lowered = line.lower()
        if bare_tx_block and "attack txs" in lowered:
            in_bare_block = True
        if bare_tx_block and in_bare_block and "reproduce tx" in lowered:
            in_bare_block = False
        url_match = any(host in lowered for host in hosts)
        if url_match or (bare_tx_block and in_bare_block):
            for tx_hash in TX_RE.findall(line):
                found.append((tx_hash.lower(), number, line))
    return found


def build_rows(archive: zipfile.ZipFile, revision: str, ground_truth: set[str]) -> tuple[list[dict], Counter, dict]:
    rows_by_chain: dict[str, list[dict]] = defaultdict(list)
    drops: Counter = Counter()
    source_metadata: list[dict] = []
    seen: set[str] = set()

    for item in SPECS:
        try:
            lines = source_lines(archive, item["path"])
        except KeyError:
            drops["missing_source_file"] += 1
            continue
        contract = find_line(lines, item["contract_pattern"])
        function = find_line(lines, item["function_pattern"])
        if contract is None:
            drops["vulnerable_contract_not_explicit"] += 1
            continue
        contract_address = ADDRESS_RE.search(contract[1])
        if contract_address is None:
            drops["vulnerable_contract_address_not_explicit"] += 1
            continue
        if function is None:
            drops["vulnerable_function_not_explicit"] += 1
            continue
        txs = transaction_lines(lines, item["chain"], item["bare_tx_block"])
        if not txs:
            drops["transaction_reference_missing"] += 1
            continue
        source_metadata.append({"path": item["path"], "chain": item["chain"], "transaction_references": len(txs)})
        for tx_hash, tx_line_number, tx_quote in txs:
            if tx_hash in ground_truth:
                drops["ground_truth_hash"] += 1
                continue
            if tx_hash in seen:
                drops["duplicate_hash"] += 1
                continue
            seen.add(tx_hash)
            rows_by_chain[item["chain"]].append(
                {
                    "chain": item["chain"],
                    "transaction_hash": tx_hash,
                    "source_poc_url": github_url(item["path"], revision),
                    "source_path": item["path"],
                    "source_transaction_line": tx_line_number,
                    "source_transaction_quote": tx_quote,
                    "vulnerable_contract": contract_address.group(0).lower(),
                    "vulnerable_contract_quote": contract[1],
                    "vulnerable_contract_line": contract[0],
                    "vulnerable_function": item["function_name"],
                    "vulnerable_function_quote": function[1],
                    "vulnerable_function_line": function[0],
                    "vulnerability_type": item["vulnerability_type"],
                    "label_status": "source_labeled_pending_trace",
                }
            )

    # Round-robin by chain keeps the frozen batch visibly multi-chain while the
    # source order above remains deterministic within each chain.
    selected: list[dict] = []
    positions = {chain: 0 for chain in SUPPORTED_CHAINS}
    while len(selected) < 40:
        progressed = False
        for chain in SUPPORTED_CHAINS:
            position = positions[chain]
            candidates = rows_by_chain[chain]
            if position >= len(candidates):
                continue
            selected.append(candidates[position])
            positions[chain] += 1
            progressed = True
            if len(selected) == 40:
                break
        if not progressed:
            break
    if len(selected) < 40:
        raise RuntimeError(f"only {len(selected)} explicit, non-ground-truth rows were available; need 40")
    for chain, candidates in rows_by_chain.items():
        drops["selected_limit"] += max(0, len(candidates) - positions.get(chain, 0))
    return selected, drops, {"sources": source_metadata, "available_by_chain": {k: len(v) for k, v in rows_by_chain.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, default=Path("benchmark/original_faultseeker/ground_truth"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    args = parser.parse_args()

    ground_truth = read_ground_truth_hashes(args.ground_truth)
    if len(ground_truth) != 115:
        raise RuntimeError(f"expected the current 115-file ground-truth directory, found {len(ground_truth)}")
    archive_sha256 = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(args.archive) as archive:
        rows, drops, discovery = build_rows(archive, args.revision, ground_truth)

    rows = sorted(rows, key=lambda row: (SUPPORTED_CHAINS.index(row["chain"]), row["transaction_hash"]))
    payload = {
        "batch_id": "batchA",
        "status": "frozen_source_labels_pending_trace",
        "collection_policy": {
            "target_rows": 40,
            "allowed_chains": list(SUPPORTED_CHAINS),
            "ground_truth_hash_count": len(ground_truth),
            "ground_truth_count_claimed_before_freeze": 114,
            "trace_performed": False,
            "rpc_or_cast_used": False,
            "scoring_performed": False,
        },
        "source": {
            "repository": f"https://github.com/{REPOSITORY}",
            "revision": args.revision,
            "archive_sha256": archive_sha256,
        },
        "counts": {
            "selected_rows": len(rows),
            "by_chain": dict(sorted(Counter(row["chain"] for row in rows).items())),
            "drop_reasons": dict(sorted(drops.items())),
            "discovery": discovery,
        },
        "rows": rows,
    }
    canonical = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    payload["artifact_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "artifact_sha256": payload["artifact_sha256"], "counts": payload["counts"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
