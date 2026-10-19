"""Pure reconstruction of the pinned upstream FaultSeeker ranker.

Source commit: ``72753bd833554449efa8499f0d1775a97fb5c696``.

This module intentionally preserves the upstream ranking semantics instead of
using the current diagnostic tie policy in ``function_ranker.py``.  It accepts
already-collected candidate evidence and performs no RPC, source retrieval, or
model calls.  It is therefore suitable for tests and for future replayed traces
without changing retained benchmark predictions.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from typing import Any


UPSTREAM_COMMIT = "72753bd833554449efa8499f0d1775a97fb5c696"

FILTERED_FUNCTIONS = frozenset({
    "totalsupply", "balanceof", "allowance", "decimals", "name", "symbol",
    "ownerof", "tokenuri", "getapproved", "isapprovedforall",
    "token0", "token1", "getreserves", "getamountout", "getamountin",
    "getamountsout", "getamountsin", "factory", "pair", "getpair",
    "paused", "owner", "admin", "ispaused", "totalshares", "pricepershare",
    "transfer", "transferfrom", "approve",
    "swapexacttokensfortokenssupportingfeeontransfertokens",
    "swapexacttokensfortokens", "swapexacttokensfornative",
    "swapexacttokensfornativetokens", "swapnativetokensfortokens",
    "swapnativetokensfortokenswithfeeontransfertokens",
})

EXTENDED_FILTERED_FUNCTIONS = FILTERED_FUNCTIONS | frozenset({
    "transferunderlyingto", "transferfromunderlying", "approveunderlying",
    "allowanceunderlying",
    "swapnativetokensfortokenswithfeeontransfertokenssupportingfeeontransfertokens",
    "algebraswapcallback",
})


def _call_record(call: dict[str, Any], *, created: bool) -> dict[str, Any]:
    record = {
        "gas": call["gas"],
        "params": call["params"] if len(call["params"]) < 200 else f"{call['params'][:200]}...",
        "depth": call["depth"],
    }
    if created:
        record["address"] = call["address"]
    return record


def rank_upstream_candidates(
    *,
    functions_to_be_inspected: dict[str, list[dict[str, Any]]],
    address_calls_with_created_contract: list[dict[str, Any]] | None = None,
    function_call_loc_memo: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Return upstream-compatible candidate maps and ordered ordinary keys.

    Ordinary candidates are keyed by ``function + '_' + address`` and count
    distinct stringified depth paths.  Equal counts retain encounter order.
    Created-contract candidates are kept in their separate upstream map.  If no
    ordinary candidate survives, the exact upstream fallback uses
    ``replace('::', '_')`` and counts every memo entry without depth
    deduplication.
    """
    ordinary: OrderedDict[str, dict[str, Any]] = OrderedDict()
    ordinary_depths: dict[str, list[str]] = {}
    created: OrderedDict[str, dict[str, Any]] = OrderedDict()
    created_depths: dict[str, list[str]] = {}
    address_list: list[str] = []

    for call in address_calls_with_created_contract or []:
        function = call["function"]
        if function.lower() in EXTENDED_FILTERED_FUNCTIONS:
            continue
        if function not in created:
            created[function] = {"count": 0, "calls": [], "address": []}
            created_depths[function] = []
        if call["address"] not in address_list:
            address_list.append(call["address"])
        depth_key = str(call["depth"])
        if depth_key not in created_depths[function]:
            created_depths[function].append(depth_key)
            created[function]["count"] += 1
            created[function]["calls"].append(_call_record(call, created=True))
            if call["address"] not in created[function]["address"]:
                created[function]["address"].append(call["address"])

    for _, calls in functions_to_be_inspected.items():
        if not calls:
            continue
        for call in calls:
            function = call["function"]
            if function.lower() in EXTENDED_FILTERED_FUNCTIONS:
                continue
            key = function + "_" + call["address"]
            if key not in ordinary:
                ordinary[key] = {"count": 0, "calls": []}
                ordinary_depths[key] = []
            if call["address"] not in address_list:
                address_list.append(call["address"])
            depth_key = str(call["depth"])
            if depth_key not in ordinary_depths[key]:
                ordinary_depths[key].append(depth_key)
                ordinary[key]["count"] += 1
                ordinary[key]["calls"].append(_call_record(call, created=False))

    fallback_used = False
    if not ordinary:
        fallback_used = True
        for function_call, calls in (function_call_loc_memo or {}).items():
            key = function_call.replace("::", "_")
            ordinary[key] = {
                "count": len(calls),
                "calls": [
                    {"gas": call["gas"], "params": call["params"], "depth": call["depth"]}
                    for call in calls
                ],
            }

    ordered_items = sorted(ordinary.items(), key=lambda item: item[1]["count"], reverse=True)
    ordered = OrderedDict((key, deepcopy(value)) for key, value in ordered_items if value["count"] > 0)
    return {
        "functions_to_be_inspected": dict(ordered),
        "address_calls_with_created_contract_in_params": dict(created),
        "address_list": address_list,
        "ordered_keys": list(ordered),
        "fallback_used": fallback_used,
        "ranking_formula": "descending count of distinct stringified depth paths; stable ties",
        "source_commit": UPSTREAM_COMMIT,
    }
