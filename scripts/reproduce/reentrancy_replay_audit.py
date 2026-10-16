"""Re-audit all labeled reentrancy rows from saved local artifacts only."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROWS = ROOT / "reports/claim_evidence/reentrancy_rows.csv"
OUT = ROOT / "reports/claim_evidence/reentrancy_replay_verification.csv"
TRACE_KEYS = ("raw_trace", "call_trace", "trace", "calls", "struct_logs")


def _artifact_has_trace(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in TRACE_KEYS:
        value = payload.get(key)
        if isinstance(value, (dict, list)) and bool(value):
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def _read_json(path: Path) -> object:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def find_trace_artifacts(chain: str, txn_hash: str) -> list[Path]:
    # Restrict the search to saved evidence directories; never acquire a trace.
    candidates = [
        ROOT / "reports" / "cohort_rebuild_v2" / "traces" / chain / f"{txn_hash}.json.gz",
        ROOT / "reports" / "historical_replay" / f"{txn_hash}.json.gz",
    ]
    found: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            if _artifact_has_trace(_read_json(path)):
                found.append(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return found


def audit_rows() -> list[dict[str, str]]:
    with ROWS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    audited = []
    for row in rows:
        paths = find_trace_artifacts(row["chain"], row["txn_hash"])
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        trace_present = bool(paths)
        audited.append({
            "row_number": row["row_number"],
            "chain": row["chain"],
            "txn_hash": row["txn_hash"],
            "label_string": row["vuln_type"],
            "saved_evidence": "local trace artifact" if trace_present else "no qualifying local trace artifact",
            "saved_replay_status": "TRACE_PRESENT" if trace_present else "TRACE_ABSENT",
            "trace_artifact_paths": " ; ".join(path.relative_to(ROOT).as_posix() for path in paths),
            "trace_sha256": " ; ".join(hashes),
            "label_verification_status": "UNVERIFIED_TRACE_PRESENT" if trace_present else "UNVERIFIED_TRACE_ABSENT",
            "verified_reentrant_count": "0",
            "verification_basis": "trace presence is not incident adjudication; no label was verified",
        })
    return audited


def main() -> None:
    rows = audit_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"rows={len(rows)} trace_present={sum(r['saved_replay_status'] == 'TRACE_PRESENT' for r in rows)} trace_absent={sum(r['saved_replay_status'] == 'TRACE_ABSENT' for r in rows)} labels_verified=0")


if __name__ == "__main__":
    main()
