"""Deterministic candidate generation from already-saved execution evidence.

The production pipeline may receive candidates from more than one trace view.
This module provides the offline-safe equivalent for saved evidence: it parses
the persisted cast trace, preserves the original candidate order, resolves a
delegatecall's caller as a proxy alias, and merges duplicate identities without
discarding supporting evidence.

No RPC, source lookup, selector service, or ground-truth data is used here.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Iterable, Mapping

from .function_ranker import canonical_call_label


_TRACE_CALL = re.compile(
    r"(?P<address>0x[0-9a-fA-F]{40})::(?P<function>[^ (]+)\([^\n]*\)"
    r"(?:\s+\[(?P<call_type>delegatecall|call|staticcall|extcall)\])?",
    re.IGNORECASE,
)
_TREE_BRANCH = re.compile(r"(?P<prefix>^[\s│|]*)[├└]─")
_CALL_TYPES = {"delegatecall", "call", "staticcall", "extcall"}


def _normalise_address(value: object) -> str:
    return str(value or "").strip().lower()


def _normalise_function(value: object) -> str:
    return canonical_call_label(str(value or "")).strip()


def _tree_depth(line: str) -> int:
    """Return a stable approximate call depth from Foundry's tree rendering."""
    match = _TREE_BRANCH.search(line)
    if not match:
        return 0
    # Last-child ancestors render as blank columns, not vertical connectors.
    # Foundry uses four columns per level; preserve both forms of indentation.
    prefix = match.group("prefix").expandtabs(4)
    return max(1, len(prefix) // 4)


def _merge_depths(destination: list, incoming: Iterable[object]) -> None:
    for depth in incoming:
        if depth not in destination:
            destination.append(depth)


def _candidate_key(candidate: Mapping[str, object]) -> tuple[str, str]:
    address = _normalise_address(
        candidate.get("code_address")
        or candidate.get("address")
        or candidate.get("contract")
        or candidate.get("callee")
    )
    function = _normalise_function(
        candidate.get("function_name")
        or candidate.get("name")
        or candidate.get("function")
    )
    return address, function


def _call_candidate(call: Mapping[str, object], *, address: str, proxy_address: str = "") -> dict:
    function = _normalise_function(call.get("function"))
    depth = int(call.get("depth") or 0)
    result = {
        "code_address": address,
        "function": function,
        "function_name": function,
        "count": 1,
        "supporting_call_depths": [[0] * depth] if depth else [[]],
        "candidate_source": "saved_trace",
        "call_types": [str(call.get("call_type") or "call").lower()],
        "trace_evidence_count": 1,
    }
    if proxy_address and proxy_address != address:
        result["proxy_address"] = proxy_address
        result["proxy_resolved"] = True
    return result


def parse_saved_trace_candidates(trace_text: str) -> list[dict]:
    """Extract call candidates and proxy aliases from a saved cast trace.

    For a delegatecall, the immediate enclosing call address is retained as a
    ``proxy_address`` and receives an alias candidate with the same function.
    Both implementation and proxy identities remain available because the
    ground-truth convention can name either side of a proxy boundary.
    """
    calls: list[dict] = []
    stack: list[tuple[int, str]] = []
    for encounter, line in enumerate(str(trace_text or "").splitlines()):
        match = _TRACE_CALL.search(line)
        if not match:
            continue
        address = _normalise_address(match.group("address"))
        function = _normalise_function(match.group("function"))
        call_type = str(match.group("call_type") or "call").lower()
        depth = _tree_depth(line)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        proxy_address = stack[-1][1] if call_type == "delegatecall" and stack else ""
        call = {
            "address": address,
            "function": function,
            "call_type": call_type if call_type in _CALL_TYPES else "call",
            "depth": depth,
            "encounter": encounter,
            "proxy_address": proxy_address,
        }
        calls.append(call)
        stack.append((depth, address))
    return calls


def merge_saved_candidates(
    candidate_sources: Iterable[Iterable[Mapping[str, object]]],
) -> list[dict]:
    """Merge candidates by normalized address and function, preserving evidence."""
    grouped: dict[tuple[str, str], dict] = {}
    encounter = 0
    for source in candidate_sources:
        for raw in source:
            candidate = deepcopy(dict(raw))
            address, function = _candidate_key(candidate)
            if not address or not function:
                continue
            key = (address, function)
            depths = list(candidate.get("supporting_call_depths") or [])
            call_types = [str(value).lower() for value in list(candidate.get("call_types") or [])]
            count = int(candidate.get("count") or 0)
            evidence_count = int(candidate.get("trace_evidence_count") or 0)
            if key not in grouped:
                candidate["code_address"] = address
                candidate["function"] = function
                candidate["function_name"] = function
                candidate["count"] = count
                candidate["supporting_call_depths"] = depths
                candidate["call_types"] = list(dict.fromkeys(call_types))
                candidate["trace_evidence_count"] = evidence_count
                candidate["_encounter"] = encounter
                grouped[key] = candidate
                encounter += 1
                continue
            current = grouped[key]
            current["count"] = int(current.get("count") or 0) + count
            current["trace_evidence_count"] = int(current.get("trace_evidence_count") or 0) + evidence_count
            _merge_depths(current.setdefault("supporting_call_depths", []), depths)
            current["call_types"] = list(dict.fromkeys(
                list(current.get("call_types") or []) + call_types
            ))
            if candidate.get("proxy_resolved"):
                current["proxy_resolved"] = True
            if candidate.get("proxy_address") and not current.get("proxy_address"):
                current["proxy_address"] = candidate["proxy_address"]
            if candidate.get("candidate_source") == "saved_trace":
                current["candidate_source"] = "saved_predictions+saved_trace"
    # ``dict`` insertion order is the evidence encounter order.  Keeping the
    # first occurrence stable is important: adding a trace view must not
    # silently reorder the frozen saved-prediction prefix.  Callers that want
    # a learned order can apply it explicitly after this merge step.
    ordered = list(grouped.values())
    for rank, candidate in enumerate(ordered, 1):
        candidate["rank"] = rank
        candidate.pop("_encounter", None)
    return ordered


def generate_saved_candidates(
    predictions: Iterable[Mapping[str, object]],
    trace_text: str = "",
    *,
    resolve_proxy: bool = True,
) -> list[dict]:
    """Generate a merged candidate list from predictions plus saved trace calls."""
    trace_candidates: list[dict] = []
    calls = parse_saved_trace_candidates(trace_text)
    for call in calls:
        trace_candidates.append(_call_candidate(call, address=call["address"]))
        if resolve_proxy and call["call_type"] == "delegatecall" and call.get("proxy_address"):
            trace_candidates.append(
                _call_candidate(
                    call,
                    address=str(call["proxy_address"]),
                    proxy_address=call["address"],
                )
            )
    return merge_saved_candidates((predictions, trace_candidates))


__all__ = [
    "generate_saved_candidates",
    "merge_saved_candidates",
    "parse_saved_trace_candidates",
]
