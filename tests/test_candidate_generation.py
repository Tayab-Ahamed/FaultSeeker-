from faultseeker.function_analysis.candidate_generation import (
    generate_saved_candidates,
    merge_saved_candidates,
    parse_saved_trace_candidates,
)


PROXY = "0x" + "11" * 20
IMPLEMENTATION = "0x" + "22" * 20
TOKEN = "0x" + "33" * 20


def test_trace_parser_preserves_call_order_and_delegatecall_parent():
    trace = (
        f"  [100] {PROXY}::upgrade()\n"
        f"    ├─ [50] {IMPLEMENTATION}::withdraw(uint256) [delegatecall]\n"
        f"    │   └─ ← [Stop]\n"
        f"    └─ [20] {TOKEN}::transfer(address,uint256)\n"
    )
    calls = parse_saved_trace_candidates(trace)
    assert [(item["address"], item["function"], item["call_type"]) for item in calls] == [
        (PROXY, "upgrade", "call"),
        (IMPLEMENTATION, "withdraw", "delegatecall"),
        (TOKEN, "transfer", "call"),
    ]
    assert calls[1]["proxy_address"] == PROXY


def test_delegatecall_generates_implementation_and_proxy_identities():
    trace = (
        f"  [100] {PROXY}::upgrade()\n"
        f"    └─ [50] {IMPLEMENTATION}::withdraw(uint256) [delegatecall]\n"
    )
    candidates = generate_saved_candidates([], trace)
    identities = {(row["code_address"], row["function"]) for row in candidates}
    assert (IMPLEMENTATION, "withdraw") in identities
    assert (PROXY, "withdraw") in identities
    proxy = next(row for row in candidates if row["code_address"] == PROXY and row["function"] == "withdraw")
    assert proxy["proxy_resolved"] is True
    assert proxy["proxy_address"] == IMPLEMENTATION


def test_duplicate_merge_sums_counts_and_deduplicates_depths_stably():
    result = merge_saved_candidates([
        [{"code_address": TOKEN, "function": "transfer", "count": 2,
          "supporting_call_depths": [[0, 1]], "trace_evidence_count": 0}],
        [{"address": TOKEN.upper(), "function_name": "transfer", "count": 1,
          "supporting_call_depths": [[0, 1], [0, 2]], "trace_evidence_count": 1}],
    ])
    assert len(result) == 1
    assert result[0]["code_address"] == TOKEN
    assert result[0]["count"] == 3
    assert result[0]["trace_evidence_count"] == 1
    assert result[0]["supporting_call_depths"] == [[0, 1], [0, 2]]


def test_merge_keeps_saved_prediction_prefix_before_trace_only_candidates():
    result = merge_saved_candidates([
        [{"code_address": PROXY, "function": "upgrade", "count": 1}],
        [{"code_address": TOKEN, "function": "transfer", "count": 1,
          "candidate_source": "saved_trace", "trace_evidence_count": 1}],
    ])
    assert [(item["code_address"], item["function"]) for item in result] == [
        (PROXY, "upgrade"),
        (TOKEN, "transfer"),
    ]


def test_nested_last_child_delegatecall_uses_immediate_parent():
    trace = (
        f"[100] {PROXY}::root()\n"
        f"    └─ [50] {TOKEN}::middle()\n"
        f"        └─ [10] {IMPLEMENTATION}::withdraw() [delegatecall]\n"
    )
    calls = parse_saved_trace_candidates(trace)
    assert calls[2]["depth"] > calls[1]["depth"]
    assert calls[2]["proxy_address"] == TOKEN
