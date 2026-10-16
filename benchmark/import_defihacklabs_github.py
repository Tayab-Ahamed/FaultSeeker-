import argparse
import csv
import io
import json
import os
import re
import urllib.request
import zipfile
from urllib.parse import urlsplit


REPO_ZIP_URL = "https://github.com/SunWeb3Sec/DeFiHackLabs/archive/refs/heads/main.zip"
DEFAULT_OUTPUT = "benchmark/imported/defihacklabs_github_candidates.csv"
DEFAULT_SUMMARY = "benchmark/imported/defihacklabs_github_candidates_summary.json"

TX_HASH_RE = re.compile(r"(?<![A-Za-z0-9_])0x[a-fA-F0-9]{64}(?![A-Za-z0-9_])")

SUPPORTED_CHAINS = {
    "eth",
    "bsc",
    "polygon",
    "arbitrum",
    "optimism",
    "avalanche",
    "base",
    "fantom",
    "gnosis",
    "zksync",
}

EXPLORER_CHAIN_HINTS = {
    "etherscan.io/tx": "eth",
    "bscscan.com/tx": "bsc",
    "polygonscan.com/tx": "polygon",
    "arbiscan.io/tx": "arbitrum",
    "optimistic.etherscan.io/tx": "optimism",
    "snowtrace.io/tx": "avalanche",
    "basescan.org/tx": "base",
    "ftmscan.com/tx": "fantom",
    "gnosisscan.io/tx": "gnosis",
    "era.zksync.network/tx": "zksync",
    "explorer.zksync.io/tx": "zksync",
}

RPC_CHAIN_HINTS = {
    "ETH_RPC_URL": "eth",
    "MAINNET_RPC_URL": "eth",
    "BSC_RPC_URL": "bsc",
    "ARBITRUM_RPC_URL": "arbitrum",
    "ARB_RPC_URL": "arbitrum",
    "POLYGON_RPC_URL": "polygon",
    "MATIC_RPC_URL": "polygon",
    "OPTIMISM_RPC_URL": "optimism",
    "AVAX_RPC_URL": "avalanche",
    "AVALANCHE_RPC_URL": "avalanche",
    "BASE_RPC_URL": "base",
    "FTM_RPC_URL": "fantom",
    "FANTOM_RPC_URL": "fantom",
    "GNOSIS_RPC_URL": "gnosis",
    "ZKSYNC_RPC_URL": "zksync",
}

FIELDNAMES = [
    "candidate_tx_hash",
    "candidate_chain",
    "source_chain",
    "supported_chain",
    "incident_id",
    "title",
    "vulnerability_type",
    "source",
    "validation_status",
    "merge_status",
    "merge_blocker",
]


def import_github_candidates(zip_url: str = REPO_ZIP_URL) -> tuple[list[dict], dict]:
    archive = download_zip(zip_url)
    rows = []
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        for name in zf.namelist():
            if not is_candidate_file(name):
                continue
            text = read_text(zf, name)
            tx_hashes = sorted({match.lower() for match in TX_HASH_RE.findall(text)})
            if not tx_hashes:
                continue
            default_chain = infer_chain(name, text)
            references = transaction_chain_references(text)
            incident_id = incident_id_from_path(name)
            title = title_from_incident_id(incident_id)
            vulnerability = infer_vulnerability(name, text)
            source = github_blob_url(name)
            for tx_hash, chain in (
                (tx, chain) for tx in tx_hashes
                for chain in sorted(references.get(tx) or {default_chain})
            ):
                supported = chain in SUPPORTED_CHAINS
                blocker = "" if supported else "Unsupported or unresolved chain; inspect PoC manually."
                rows.append(
                    {
                        "candidate_tx_hash": tx_hash,
                        "candidate_chain": chain,
                        "source_chain": chain,
                        "supported_chain": supported,
                        "incident_id": incident_id,
                        "title": title,
                        "vulnerability_type": vulnerability,
                        "source": source,
                        "validation_status": "source_poc_tx_candidate_pending_rpc",
                        "merge_status": "staged_not_merged",
                        "merge_blocker": blocker,
                    }
                )
    rows = dedupe_rows(rows)
    return rows, summarize_rows(rows)


def download_zip(zip_url: str) -> bytes:
    request = urllib.request.Request(zip_url, headers={"User-Agent": "FaultSeekerResearch/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def is_candidate_file(path: str) -> bool:
    lowered = path.lower()
    return lowered.endswith((".sol", ".md", ".txt")) and not any(
        part in lowered for part in ["/lib/", "/node_modules/", "/cache/", "/out/"]
    )


def read_text(zf: zipfile.ZipFile, name: str) -> str:
    try:
        return zf.read(name).decode("utf-8", errors="ignore")
    except KeyError:
        return ""


def transaction_chain_references(text: str) -> dict[str, set[str]]:
    """Resolve only explicit transaction URLs on exact known explorer hosts.

    A multi-chain PoC does not assign one chain to all its hashes. References
    remain unverified leads; neither URL extraction nor a valid hex width
    establishes an exploit role or RPC acceptance.
    """
    explorer_hosts = {hint.split('/')[0]: chain for hint, chain in EXPLORER_CHAIN_HINTS.items()}
    references: dict[str, set[str]] = {}
    for url in re.findall(r"https?://[^\s<>\"'\)\]]+", text):
        try:
            parsed = urlsplit(url.rstrip('.,;'))
        except ValueError:
            continue
        host = (parsed.hostname or '').lower().removeprefix('www.')
        chain = explorer_hosts.get(host)
        match = re.fullmatch(r'/tx/(0x[a-fA-F0-9]{64})/?', parsed.path)
        if host in {'phalcon.blocksec.com', 'explorer.phalcon.xyz'}:
            match = re.fullmatch(r'/tx/([a-z]+)/(?P<tx>0x[a-fA-F0-9]{64})/?', parsed.path)
            if match:
                chain = match[1] if match[1] in SUPPORTED_CHAINS else None
        if not match or not chain:
            continue
        tx_hash = (match['tx'] if host in {'phalcon.blocksec.com', 'explorer.phalcon.xyz'} else match[1]).lower()
        references.setdefault(tx_hash, set()).add(chain)
    return references


def infer_chain(path: str, text: str) -> str:
    lowered = f"{path}\n{text}".lower()
    explicit = {chain for chains in transaction_chain_references(text).values() for chain in chains}
    if explicit:
        return next(iter(explicit)) if len(explicit) == 1 else 'unknown'
    rpc_chains = {chain for needle, chain in RPC_CHAIN_HINTS.items() if needle.lower() in lowered}
    if rpc_chains:
        return next(iter(rpc_chains)) if len(rpc_chains) == 1 else 'unknown'
    path_parts = {part.lower() for part in path.replace("\\", "/").split("/")}
    path_chains = SUPPORTED_CHAINS & path_parts
    if path_chains:
        return next(iter(path_chains)) if len(path_chains) == 1 else 'unknown'
    if "ethereum" in lowered or "mainnet" in lowered:
        return "eth"
    return "unknown"


def incident_id_from_path(path: str) -> str:
    basename = os.path.splitext(os.path.basename(path))[0]
    parent = os.path.basename(os.path.dirname(path))
    candidate = basename if basename.lower() not in {"test", "exploit"} else parent
    return slugify(candidate)


def title_from_incident_id(incident_id: str) -> str:
    return incident_id.replace("_", " ").replace("-", " ").strip().title()


def infer_vulnerability(path: str, text: str) -> str:
    lowered = f"{path}\n{text}".lower()
    checks = [
        ("reentr", "Reentrancy"),
        ("flashloan", "Flash Loan Attack"),
        ("flash loan", "Flash Loan Attack"),
        ("oracle", "Oracle Manipulation"),
        ("price", "Price Manipulation"),
        ("access control", "Access Control"),
        ("delegatecall", "Delegatecall Abuse"),
        ("precision", "Precision Loss"),
        ("rounding", "Precision Loss"),
        ("governance", "Governance Attack"),
        ("bridge", "Bridge Exploit"),
        ("sandwich", "MEV/Sandwich"),
        ("mev", "MEV/Sandwich"),
        ("inflation", "Inflation Attack"),
        ("mint", "Inflation Attack"),
    ]
    for needle, label in checks:
        if needle in lowered:
            return label
    return "Unknown"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "unknown-incident"


def github_blob_url(path: str) -> str:
    parts = path.replace("\\", "/").split("/", 1)
    relative = parts[1] if len(parts) == 2 else path
    return f"https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/{relative}"


def dedupe_rows(rows: list[dict]) -> list[dict]:
    deduped = {}
    for row in rows:
        key = (row["candidate_tx_hash"], row["candidate_chain"])
        deduped.setdefault(key, row)
    return sorted(deduped.values(), key=lambda row: (row["candidate_chain"], row["candidate_tx_hash"]))


def summarize_rows(rows: list[dict]) -> dict:
    chain_counts: dict[str, int] = {}
    vuln_counts: dict[str, int] = {}
    supported = 0
    for row in rows:
        chain_counts[row["candidate_chain"]] = chain_counts.get(row["candidate_chain"], 0) + 1
        vuln_counts[row["vulnerability_type"]] = vuln_counts.get(row["vulnerability_type"], 0) + 1
        if row["supported_chain"]:
            supported += 1
    return {
        "candidate_rows": len(rows),
        "supported_candidate_rows": supported,
        "unsupported_candidate_rows": len(rows) - supported,
        "source": "github:SunWeb3Sec/DeFiHackLabs",
        "validation_status": "source_poc_tx_candidate_pending_rpc",
        "chain_counts": sort_counts(chain_counts),
        "vulnerability_counts": sort_counts(vuln_counts),
    }


def sort_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def write_rows(rows: list[dict], output_csv: str) -> None:
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(summary: dict, output_json: str) -> None:
    os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import DeFiHackLabs GitHub PoC transaction hash candidates.")
    parser.add_argument("--zip-url", default=REPO_ZIP_URL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows, summary = import_github_candidates(args.zip_url)
    write_rows(rows, args.output)
    write_summary(summary, args.summary_output)
    print(json.dumps({"output": args.output, "summary_output": args.summary_output, **summary}, indent=2))


if __name__ == "__main__":
    main()
