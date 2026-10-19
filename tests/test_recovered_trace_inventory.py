import json


def test_inventory_distinguishes_recovered_calltrees_and_blocked_bsc():
    from scripts.research.audit_recovered_trace_inventory import run

    result = run()
    json.dumps(result)
    assert len(result["rows"]) == 15
    assert result["recovery_class_counts"]["captured_trace_recovered_but_function_gt_unavailable"] == 9
    assert result["recovery_class_counts"]["external_capture_failed_local_trace_recovered_but_function_gt_unavailable"] == 4
    assert result["recovery_class_counts"]["externally_blocked_no_local_call_tree"] == 2
