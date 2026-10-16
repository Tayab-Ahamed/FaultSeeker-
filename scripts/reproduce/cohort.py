import csv
import re
from collections import Counter

from common import COHORT, ROOT, read_csv, run


def compute():
    """Count the frozen historical cohort and print its chain distribution."""
    rows = read_csv(COHORT)
    counts = Counter(r["chain"] for r in rows)
    print("Chain | Rows")
    for chain, count in sorted(counts.items()):
        print(f"{chain} | {count}")
    print(f"Unique chain/hash pairs={len({(r['chain'], r['txn_hash']) for r in rows})}")
    print("Historical candidates only; do not confuse this population with the newer admitted cohort.")
    return {"cohort_rows": len(rows), "chain_count": len(counts)}


def write_provenance():
    rows = read_csv(COHORT)
    path = ROOT / "reports/reproducibility/cohort_provenance.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["tx_hash", "chain", "source_link", "label_source"])
        writer.writeheader()
        for row in rows:
            # Copy only explicit URLs from this exact row; no invented explorer links.
            # One legacy row has an unbalanced quote instead of valid JSON.
            # Extract its explicitly present URL without repairing or guessing it.
            links = re.findall(r"https?://[^\s\x22\x27\[\]<>]+", row["analysis"])
            writer.writerow({"tx_hash": row["txn_hash"], "chain": row["chain"],
                             "source_link": " ; ".join(links) if links else "no source",
                             "label_source": COHORT.relative_to(ROOT).as_posix() + ":vuln_type"})
    print(f"Wrote {path}; rows={len(rows)}; URLs copied, not fetched or independently verified.")


if __name__ == "__main__":
    raise SystemExit(run(compute, write_provenance))
