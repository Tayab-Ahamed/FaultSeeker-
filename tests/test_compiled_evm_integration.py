"""Real compiler/EVM integration; never substitute hand-authored opcode logs."""
import importlib.util
from pathlib import Path
import socket

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compiled_fixture_runner", ROOT / "scripts/replay_evm_fixtures.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.fixture(scope="module")
def executed_cases(tmp_path_factory):
    tools, missing = runner.resolve_tools()
    if missing:
        pytest.skip("Real EVM integration requires: " + ", ".join(missing))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    output = tmp_path_factory.mktemp("compiled-evm") / "trace.json"
    return runner.replay(output, tools, port=port)


def test_compiled_contracts_emit_real_storage_opcodes(executed_cases):
    assert executed_cases["authentic_execution"] is True
    assert set(executed_cases["cases"]) == {"reentrant", "guarded", "delegatecall"}
    for case in executed_cases["cases"].values():
        assert case["receipt"]["status"] in ("0x1", 1, "1")
        operations = {step["op"] for step in case["opcode_trace"]["structLogs"]}
        assert {"SLOAD", "SSTORE"} <= operations


def test_compiled_mutex_preserves_actual_lock_transitions(executed_cases):
    from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
    from faultseeker.utils.rpc_provider import normalize_trace_node
    case = executed_cases["cases"]["guarded"]
    storage = normalize_opcode_storage_trace(
        case["opcode_trace"]["structLogs"], normalize_trace_node(case["call_trace"]))
    assert storage["normalization_complete"] is True
    writes = [event for event in storage["storage_events"]
              if int(event["slot"], 16) == 1]
    assert [(int(event["value_before"], 16), int(event["value_after"], 16))
            for event in writes] == [(1, 2), (2, 1)]


def test_compiled_delegatecall_writes_proxy_storage(executed_cases):
    from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
    from faultseeker.utils.rpc_provider import normalize_trace_node
    case = executed_cases["cases"]["delegatecall"]
    root = normalize_trace_node(case["call_trace"])
    storage = normalize_opcode_storage_trace(case["opcode_trace"]["structLogs"], root)
    assert storage["normalization_complete"] is True
    assert storage["storage_events"]
    assert all(event["address"] == root["callee"].lower()
               for event in storage["storage_events"])
    assert any(int(event["value_after"], 16) == 42
               for event in storage["storage_events"])


@pytest.mark.parametrize("name,tier", [
    ("reentrant", "CONFIRMED_REENTRANCY"),
    ("guarded", "POSSIBLE_REENTRANCY"),
    ("delegatecall", "NOT_REENTRANCY")])
def test_paper_tiers_on_compiled_contracts(executed_cases, name, tier):
    from benchmark.detector_experiments import detector_observation
    case = executed_cases["cases"][name]
    observation = detector_observation({"raw_trace": {
        "call": case["call_trace"], "opcode": case["opcode_trace"]}}, "full")
    detail = observation["detector_result"]
    assert detail["tier"] == tier
    if name == "guarded":
        # The published weights/threshold still flag this blocked attempt.
        # Preserve and expose that false positive instead of tuning it away.
        assert detail["score"] == pytest.approx(0.35)
        assert observation["predicted_exploit"] is True
        assert detail["signals"]["same_function_reentry"] is False
        assert detail["signals"]["state_slot_reentry"] is False
