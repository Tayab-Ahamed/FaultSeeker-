"""Regression tests for canonical function/selector identities."""

from benchmark.generate_pipeline_predictions import serialize_ranked_candidates
from faultseeker.function_analysis.function_ranker import (
    RankingResult,
    canonical_call_label,
)


def test_bare_four_byte_selector_is_canonicalized_without_changing_names():
    assert canonical_call_label("ba381f8f") == "ba381f8f"
    assert canonical_call_label("BA381F8F") == "BA381F8F"
    assert canonical_call_label("receiveFlashLoan") == "receiveFlashLoan"
    assert canonical_call_label("deposit(address)") == "deposit(address)"


def test_pipeline_serializer_preserves_canonical_selector_identity():
    result = RankingResult(
        ranked_functions=[
            {
                "rank": 1,
                "code_address": "0x00c409001c1900ddcda20000008e112417db003b",
                "function": canonical_call_label("ba381f8f"),
                "selector": "0xba381f8f",
                "count": 1,
                "supporting_call_depths": [[1]],
            }
        ]
    )
    serialized = serialize_ranked_candidates(result)
    assert serialized[0]["function"] == "0xba381f8f"
    assert serialized[0]["code_address"] == "0x00c409001c1900ddcda20000008e112417db003b"
    assert serialized[0]["rank"] == 1
    assert serialized[0]["supporting_call_depths"] == [[1]]
