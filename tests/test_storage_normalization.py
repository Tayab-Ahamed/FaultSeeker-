from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace


def test_reverted_delegate_write_does_not_poison_following_parent_read():
    word = lambda value: f'0x{value:064x}'
    owner, implementation = '0x'+'11'*20, '0x'+'22'*20
    root = {'callee': owner, 'children': [{'callee': implementation, 'success': False, 'children': []}]}
    logs = [
        {'depth': 1, 'op': 'SLOAD', 'stack': [word(1)]},
        {'depth': 1, 'op': 'POP', 'stack': [word(10)]},
        {'depth': 1, 'op': 'DELEGATECALL', 'stack': [word(10), word(int(implementation,16)), word(100)]},
        {'depth': 2, 'op': 'SSTORE', 'stack': [word(99), word(1)]},
        {'depth': 2, 'op': 'REVERT', 'stack': []},
        {'depth': 1, 'op': 'SLOAD', 'stack': [word(1)]},
        {'depth': 1, 'op': 'STOP', 'stack': [word(10)]},
    ]
    normalized = normalize_opcode_storage_trace(logs, root)
    assert normalized['storage_events'][0]['reverted'] is True
    assert normalized['storage_reads'][-1]['value'] == word(10)
from faultseeker.data_collection.txn_replayer import TransactionReplayer


def _word(value):
    return f"0x{value:064x}"


def test_raw_sload_then_sstore_preserves_slot_value_and_program_counters():
    owner = "0x" + "11" * 20
    logs = [
        {"depth": 1, "pc": 4, "op": "SLOAD", "stack": [_word(7)], "storage": {_word(7): _word(3)}},
        {"depth": 1, "pc": 5, "op": "PUSH1", "stack": [_word(3)]},
        {"depth": 1, "pc": 9, "op": "SSTORE", "stack": [_word(4), _word(7)], "storage": {_word(7): _word(3)}},
    ]
    normalized = normalize_opcode_storage_trace(logs, {"callee": owner, "call_id": "0", "success": True})
    assert normalized["storage_reads"] == [{"address": owner, "slot": _word(7), "value": _word(3), "pc": 4, "depth": 1, "call_id": "0", "event_index": 0, "reverted": False}]
    assert normalized["storage_events"][0]["value_before"] == _word(3)
    assert normalized["storage_events"][0]["value_after"] == _word(4)
    assert normalized["storage_events"][0]["pc"] == 9
    assert normalized["storage_events"][0]["event_index"] == 2


def test_delegatecall_uses_proxy_storage_and_marks_reverted_child_writes():
    proxy = "0x" + "11" * 20
    implementation = "0x" + "22" * 20
    root = {"callee": proxy, "success": True, "children": [
        {"callee": implementation, "call_type": "DELEGATECALL", "success": False, "children": []}
    ]}
    logs = [
        {"depth": 1, "pc": 1, "op": "DELEGATECALL", "stack": [_word(int(implementation, 16)), _word(100)]},
        {"depth": 2, "pc": 2, "op": "SSTORE", "stack": [_word(9), _word(7)]},
        {"depth": 2, "pc": 3, "op": "REVERT", "stack": []},
        {"depth": 1, "pc": 4, "op": "SSTORE", "stack": [_word(8), _word(7)]},
    ]
    writes = normalize_opcode_storage_trace(logs, root)["storage_events"]
    assert [event["address"] for event in writes] == [proxy, proxy]
    assert [event["call_id"] for event in writes] == ["0.0", "0"]
    assert [event["reverted"] for event in writes] == [True, False]
    assert writes[1]["after_external_call"] is True


def test_structured_trace_cache_is_chain_and_tracer_scoped(tmp_path):
    replayer = TransactionReplayer(str(tmp_path / "text"), str(tmp_path / "structured"))
    tx = "0x" + "ab" * 32
    result = {"schema_version": 2, "transaction_hash": tx, "chain": "eth", "trace": {}}
    replayer.cache_structured_trace(tx, result, "eth")
    assert replayer.get_structured_cache(tx, "eth") == result
    assert replayer.get_structured_cache(tx, "bsc") is None
    replayer.cache_replay(tx, "eth trace", "eth")
    assert replayer.get_replay_cache(tx, "bsc") is None


def test_rpc_trace_uses_opcode_normalizer_and_reports_coverage(monkeypatch):
    import faultseeker.data_collection.txn_replayer as replay_module

    owner = "0x" + "11" * 20
    responses = {
        "callTracer": {"type": "CALL", "from": "0x" + "aa" * 20, "to": owner,
                       "input": "0x", "calls": []},
        "opcode": {"structLogs": [
            {"depth": 1, "pc": 1, "op": "SLOAD", "stack": [_word(3)], "storage": {_word(3): _word(2)}},
            {"depth": 1, "pc": 2, "op": "SSTORE", "stack": [_word(4), _word(3)]},
        ]},
        "stateDiff": {"trace": [], "stateDiff": {}},
    }

    def rpc_call(_chain, method, params, timeout):
        if method == "trace_replayTransaction":
            return responses["stateDiff"]
        return responses["callTracer" if params[1].get("tracer") else "opcode"]

    monkeypatch.setattr(replay_module, "rpc_call", rpc_call)
    result = TransactionReplayer._rpc_structured_trace("0x" + "ab" * 32, "eth")
    assert result["storage_reads"][0]["value"] == _word(2)
    assert result["storage_events"][0]["value_after"] == _word(4)
    assert result["trace_coverage"] == {
        "trace_complete": True, "token_flow_complete": False, "storage_trace_complete": True,
        "multi_tx_context_complete": False,
    }


def test_local_fixture_runner_orchestrates_deploy_transact_and_both_tracers(monkeypatch):
    from scripts import replay_evm_fixtures as runner

    commands = []
    rpc_methods = []
    deploy_count = 0

    def command(args, input_text=None):
        nonlocal deploy_count
        commands.append(args)
        if "--create" in args:
            deploy_count += 1
            return __import__("json").dumps({"status": "0x1", "contractAddress": f"0x{deploy_count:040x}",
                                               "transactionHash": f"0x{deploy_count:064x}"})
        return __import__("json").dumps({"status": "0x1", "transactionHash": f"0x{len(commands):064x}"})

    def rpc(_url, method, params):
        rpc_methods.append((method, params))
        return {"structLogs": []} if not params[1].get("tracer") else {"type": "CALL", "calls": []}

    monkeypatch.setattr(runner, "_command", command)
    monkeypatch.setattr(runner, "_rpc", rpc)
    compiled = {source: {contract: {"evm": {"bytecode": {"object": "6000"}}}
                         for contract in contracts}
                for source, contracts in {
                    "ReentrancyCases.sol": ["VulnerableVault", "RecursiveAttacker"],
                    "GuardCases.sol": ["GuardedVault", "GuardProbe"],
                    "ProxyCases.sol": ["StorageProxy", "ProxyImplementation"],
                }.items()}
    cases = runner.execute_cases(compiled, "cast", "http://127.0.0.1:18545")
    assert set(cases) == {"reentrant", "guarded", "delegatecall"}
    assert sum("--create" in command for command in commands) == 6
    assert any("attack()" in command for command in commands)
    assert any("setValue(uint256)" in command for command in commands)
    assert len(rpc_methods) == 6
    assert {config[1].get("tracer", "opcode") for _, config in rpc_methods} == {"callTracer", "opcode"}
