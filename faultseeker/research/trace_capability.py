"""Opt-in eligibility decisions for reentrancy observations.

The normal detector remains unchanged.  This module prevents callers from
describing a structural fallback as storage-backed evidence and records the
minimum capture facts needed to audit a result locally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TraceCapability:
    chain: str = ""
    transaction_hash: str = ""
    trace_complete: bool = False
    storage_trace_complete: bool = False
    canonical_trace_present: bool = False
    storage_event_count: int = 0
    receipt_identity_verified: bool = False
    provider: str = ""
    capture_kind: str = "unknown"

    @classmethod
    def from_capture(cls, capture: Mapping[str, Any] | None) -> "TraceCapability":
        capture = capture or {}
        coverage = capture.get("trace_coverage") or {}
        trace = capture.get("canonical_trace") or capture.get("trace")
        events = capture.get("storage_events") or []
        return cls(
            chain=str(capture.get("chain") or ""),
            transaction_hash=str(capture.get("transaction_hash") or capture.get("txn_hash") or ""),
            trace_complete=coverage.get("trace_complete") is True,
            storage_trace_complete=coverage.get("storage_trace_complete") is True,
            canonical_trace_present=isinstance(trace, (dict, list)) and bool(trace),
            storage_event_count=len(events) if isinstance(events, list) else 0,
            receipt_identity_verified=capture.get("receipt_identity_verified") is True,
            provider=str(capture.get("provider") or capture.get("trace_provider") or ""),
            capture_kind=str(capture.get("capture_kind") or capture.get("source") or "unknown"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TraceEligibility:
    eligible: bool
    mode: str
    reasons: tuple[str, ...]
    capability: TraceCapability

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["capability"] = self.capability.to_dict()
        return payload


def assess_reentrancy_trace(
    capture: Mapping[str, Any] | TraceCapability | None,
    *,
    require_storage: bool = False,
    require_receipt_identity: bool = False,
) -> TraceEligibility:
    """Classify a capture as storage-backed, structural fallback, or ineligible.

    This is deliberately conservative: a trace with no canonical tree is not
    eligible, and storage mode requires an explicitly complete opcode capture.
    Empty storage events are allowed in storage mode because a complete trace
    can legitimately contain no SSTORE; callers can inspect the count.
    """
    capability = capture if isinstance(capture, TraceCapability) else TraceCapability.from_capture(capture)
    reasons: list[str] = []
    if not capability.trace_complete:
        reasons.append("trace_incomplete")
    if not capability.canonical_trace_present:
        reasons.append("canonical_trace_missing")
    if require_receipt_identity and not capability.receipt_identity_verified:
        reasons.append("receipt_identity_unverified")

    if capability.trace_complete and capability.canonical_trace_present and capability.storage_trace_complete:
        if require_receipt_identity and not capability.receipt_identity_verified:
            return TraceEligibility(False, "ineligible", tuple(reasons), capability)
        return TraceEligibility(True, "storage", tuple(reasons), capability)

    if require_storage:
        if not capability.storage_trace_complete:
            reasons.append("storage_trace_incomplete")
        return TraceEligibility(False, "ineligible", tuple(dict.fromkeys(reasons)), capability)

    if capability.trace_complete and capability.canonical_trace_present:
        reasons.append("storage_trace_unavailable_structural_fallback")
        return TraceEligibility(True, "structural", tuple(reasons), capability)
    return TraceEligibility(False, "ineligible", tuple(dict.fromkeys(reasons)), capability)
