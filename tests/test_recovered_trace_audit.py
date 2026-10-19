import json

from scripts.research.audit_recovered_traces import observed_calls


def test_observed_calls_preserves_raw_selector_and_nested_order():
    raw = {
        "requests": [{
            "method": "debug_traceTransaction",
            "response": {"body": {"result": {
                "to": "0x" + "11" * 20,
                "input": "0xaaaaaaaa" + "00" * 32,
                "calls": [{
                    "to": "0x" + "22" * 20,
                    "input": "0xbbbbbbbb" + "00" * 32,
                    "calls": [{
                        "to": "0x" + "11" * 20,
                        "input": "0xaaaaaaaa" + "11" * 32,
                    }],
                }],
            }}}
        }]
    }

    assert observed_calls(raw) == [
        {"address": "0x" + "11" * 20, "selector": "0xaaaaaaaa"},
        {"address": "0x" + "22" * 20, "selector": "0xbbbbbbbb"},
    ]


def test_audit_result_is_json_serializable():
    from scripts.research.audit_recovered_traces import run

    result = run()
    json.dumps(result)
    assert result["summary"]["captured_rows"] == 9
    assert result["summary"]["captured_rows_with_original_ground_truth"] == 4
    assert result["summary"]["captured_rows_with_exact_function_identity"] == 4
