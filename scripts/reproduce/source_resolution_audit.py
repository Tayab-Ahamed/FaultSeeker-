"""Audit frozen-cohort hash and source-URL reachability using free HTTP only."""

import csv
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / "reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv"
OUT = ROOT / "reports/claim_evidence/source_resolution_audit.csv"
URL_RE = re.compile(r"https?://[^\s\"'\[\]<>]+")
HASH_RE = re.compile(r"0x[0-9a-fA-F]{64}\Z")


def probe(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FaultSeeker-local-source-audit/1.0", "Range": "bytes=0-0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return url, response.status, "resolved"
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            return url, error.code, "redirect"
        return url, error.code, "http_error"
    except Exception as error:
        return url, type(error).__name__, "unresolved"


def main():
    with COHORT.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    urls = sorted({url.rstrip(".,);]") for row in rows for url in URL_RE.findall(row.get("analysis", ""))})
    results = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(probe, url) for url in urls]
        for future in as_completed(futures):
            url, code, status = future.result()
            results[url] = (code, status)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "row_number", "chain", "txn_hash", "hash_valid", "source_url_count",
            "resolved_url_count", "source_status", "source_urls",
        ], lineterminator="\n")
        writer.writeheader()
        for row_number, row in enumerate(rows, 2):
            row_urls = [url.rstrip(".,);]") for url in URL_RE.findall(row.get("analysis", ""))]
            resolved = [url for url in row_urls if results.get(url, (None, "unresolved"))[1] in {"resolved", "redirect"}]
            writer.writerow({
                "row_number": row_number,
                "chain": row.get("chain", ""),
                "txn_hash": row.get("txn_hash", ""),
                "hash_valid": str(bool(HASH_RE.fullmatch(row.get("txn_hash", "").strip()))).lower(),
                "source_url_count": len(row_urls),
                "resolved_url_count": len(resolved),
                "source_status": "RESOLVED" if resolved else "UNRESOLVED",
                "source_urls": " ; ".join(f"{url} [{results.get(url, ('?', 'unresolved'))[0]}]" for url in row_urls),
            })
    unresolved = sum(not any(results.get(url, (None, "unresolved"))[1] in {"resolved", "redirect"} for url in [u.rstrip(".,);]") for u in URL_RE.findall(row.get("analysis", ""))]) for row in rows)
    invalid_hash = sum(not bool(HASH_RE.fullmatch(row.get("txn_hash", "").strip())) for row in rows)
    print(f"rows={len(rows)} urls={len(urls)} unresolved_rows={unresolved} invalid_hashes={invalid_hash}")


if __name__ == "__main__":
    main()
