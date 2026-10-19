import json

from scripts.research.evaluate_recovered_trace_localization import (
    _iter_calls,
    trace_text_from_calltree,
)


def test_trace_text_adapter_uses_observed_selector_not_ground_truth_label():
    trace = {
        "to": "0x" + "11" * 20,
        "input": "0xaaaaaaaa" + "00" * 32,
        "calls": [{
            "to": "0x" + "22" * 20,
            "input": "0xbbbbbbbb" + "00" * 32,
            "type": "DELEGATECALL",
        }],
    }
    text = trace_text_from_calltree(trace)
    assert "0x" + "11" * 20 + "::0xaaaaaaaa()" in text
    assert "0x" + "22" * 20 + "::0xbbbbbbbb()" in text
    assert "cacheAssetPrice" not in text
    assert len(list(_iter_calls(trace))) == 2


def test_recovered_trace_localization_artifact_is_paired_and_exploratory():
    from scripts.research.evaluate_recovered_trace_localization import run

    result = run()
    json.dumps(result)
    assert result["eligibility"]["rows"] == 4
    assert result["eligibility"]["newly_recovered_rows"] == 0
    assert result["eligibility"]["batch_b_c_read"] is False
    assert result["decision"] == "EXPLORATORY_ONLY_NOT_PRODUCTION_ADOPTED"
    assert [row["overlap_group"] for row in result["rows"]] == [
        "preexisting_four_original_overlap"
    ] * 4
