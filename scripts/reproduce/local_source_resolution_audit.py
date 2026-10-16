"""Search unresolved source URLs in already-present local source files.

No URL is opened.  A local match records source-string presence only and is
never treated as incident adjudication.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/claim_evidence/source_resolution_audit.csv"
OUT = ROOT / "reports/claim_evidence/source_resolution_local_audit.csv"
SUMMARY = ROOT / "reports/claim_evidence/source_resolution_local_summary.json"
URL_RE = re.compile(r"https?://[^\s\"'\[\]<>]+")
SOURCE_ROOTS = {
    "DeFiHackLabs": (ROOT / "DeFiHackLabs", ROOT / "benchmark" / "DeFiHackLabs"),
    "rekt": (ROOT / "rekt", ROOT / "benchmark" / "rekt"),
    "DeFiLlama": (ROOT / "benchmark" / "imported" / "defillama_hacks.full.csv",),
}
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt", ".sol", ".yaml", ".yml"}


def _files_for_source(name: str) -> list[Path]:
    files: list[Path] = []
    for base in SOURCE_ROOTS[name]:
        if base.is_file():
            files.append(base)
        elif base.is_dir():
            files.extend(path for path in base.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)
    return sorted(set(files))


def _index() -> dict[str, list[tuple[Path, str, str]]]:
    index: dict[str, list[tuple[Path, str, str]]] = {}
    for source_name in SOURCE_ROOTS:
        entries = []
        for path in _files_for_source(source_name):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            entries.append((path, hashlib.sha256(path.read_bytes()).hexdigest(), text))
        index[source_name] = entries
    return index


def audit() -> tuple[list[dict[str, str]], dict]:
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unresolved_rows = [row for row in rows if row["source_status"] == "UNRESOLVED"]
    index = _index()
    output: list[dict[str, str]] = []
    for row in unresolved_rows:
        urls = [url.rstrip(".,);]") for url in URL_RE.findall(row["source_urls"])]
        # The existing artifact has one row per benchmark row.  Its bracketed
        # status is retained as input metadata; only the URL before the bracket
        # is searched locally.
        urls = [url.split(" [", 1)[0] for url in urls]
        for url in urls:
            attempts = []
            matches = []
            for source_name, entries in index.items():
                attempts.append(source_name)
                for path, digest, text in entries:
                    if url in text:
                        matches.append(f"{source_name}:{path.relative_to(ROOT).as_posix()}#{digest}")
            output.append({
                "row_number": row["row_number"],
                "chain": row["chain"],
                "txn_hash": row["txn_hash"],
                "source_url": url,
                "local_sources_attempted": " ; ".join(attempts),
                "local_resolution": "LOCAL_SOURCE_STRING_FOUND" if matches else "NO_LOCAL_SOURCE_MATCH",
                "matching_local_files": " ; ".join(matches),
                "adjudication_status": "NOT_PERFORMED",
                "resolution_note": "A local string match, if any, is not incident adjudication.",
            })
    summary = {
        "input": INPUT.relative_to(ROOT).as_posix(),
        "unresolved_rows_attempted": len(unresolved_rows),
        "unresolved_urls_attempted": len(output),
        "unresolved_source_url_rows": len(unresolved_rows),
        "local_resolutions": sum(row["local_resolution"] == "LOCAL_SOURCE_STRING_FOUND" for row in output),
        "incident_adjudications": 0,
        "network_requests": 0,
        "source_roots": {
            name: {
                "present": any(path.exists() for path in paths),
                "files_scanned": len(index[name]),
            }
            for name, paths in SOURCE_ROOTS.items()
        },
        "scope": "local DeFiHackLabs, rekt, and already-present DeFiLlama files only",
    }
    return output, summary


def main() -> None:
    rows, summary = audit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
