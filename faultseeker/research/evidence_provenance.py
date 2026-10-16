"""Opt-in digest-bound provenance for evidence cards and reports."""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


KINDS = frozenset({"observed", "derived", "synthetic"})


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    kind: str
    artifact: str
    sha256: str
    description: str = ""
    validated: bool = True

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        if len(self.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.sha256.lower()):
            raise ValueError("sha256 must be a lowercase hexadecimal digest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceLedger:
    """A small local manifest; it never fetches URLs or reads environment files."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).resolve()
        self.records: list[EvidenceRecord] = []

    def _safe_path(self, artifact: str | os.PathLike[str]) -> Path:
        path = (self.root / Path(artifact)).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("artifact path escapes evidence root")
        return path

    def add_artifact(
        self,
        evidence_id: str,
        artifact: str | os.PathLike[str],
        *,
        kind: str = "observed",
        description: str = "",
        expected_sha256: str | None = None,
    ) -> EvidenceRecord:
        path = self._safe_path(artifact)
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256.lower():
            raise ValueError("artifact digest mismatch")
        record = EvidenceRecord(evidence_id, kind, path.relative_to(self.root).as_posix(), digest, description)
        self.records.append(record)
        return record

    def manifest(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.records]

    def validate_for_claim(self, *, allow_derived: bool = True, allow_synthetic: bool = False) -> None:
        """Raise when a ledger contains evidence not eligible for an empirical claim."""
        for record in self.records:
            if not record.validated:
                raise ValueError(f"unvalidated evidence: {record.evidence_id}")
            if record.kind == "synthetic" and not allow_synthetic:
                raise ValueError(f"synthetic evidence is not eligible: {record.evidence_id}")
            if record.kind == "derived" and not allow_derived:
                raise ValueError(f"derived evidence is not eligible: {record.evidence_id}")


def attach_provenance(card: dict[str, Any], ledger: EvidenceLedger, *, require_observed: bool = False) -> dict[str, Any]:
    """Return a copy of an evidence card with explicit provenance metadata."""
    if require_observed:
        ledger.validate_for_claim(allow_derived=False, allow_synthetic=False)
    result = dict(card)
    result["evidence_provenance"] = ledger.manifest()
    return result
