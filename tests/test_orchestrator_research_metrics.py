from faultseeker.forensics.orchestrator import ForensicsOrchestrator


def test_trace_entropy_is_normalized():
    flat = [
        {"function": "swap"},
        {"function": "swap"},
        {"function": "transfer"},
        {"function": "withdraw"},
    ]

    entropy = ForensicsOrchestrator._trace_entropy(flat)

    assert 0.0 < entropy <= 1.0


def test_trace_entropy_handles_empty_trace():
    assert ForensicsOrchestrator._trace_entropy([]) == 0.0
