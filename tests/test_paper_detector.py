from faultseeker.forensics.signal_extractor import SignalExtractor
from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
from faultseeker.core.paper_profile import score_reentrancy, reentrancy_tier


def _extract(trace, writes):
    return SignalExtractor(
        txn_seq={},
        tx_analysis={"trace": {}, "canonical_trace": trace, "storage_events": writes,
                     "flatten_trace": [], "repeated_patterns": {}},
        paper_mode=True,
    ).run().raw


def _word(number):
    return f"0x{number:064x}"


def test_paper_profile_uses_five_tiers_and_actual_storage_signals():
    owner = "0x" + "11" * 20
    root = {"callee": owner, "caller": "0x" + "aa" * 20,
            "call_type": "CALL", "function_selector": "0xdeadbeef", "depth": 0,
            "children": []}
    one_write = [{"address": owner, "slot": _word(1), "value_after": _word(2),
                  "depth": 1, "pc": 1, "event_index": 0,
                  "after_external_call": True}]
    raw = _extract(root, one_write)
    assert raw["reentrancy_score"] == 0.25
    assert raw["reentrancy_confidence_tier"] == "UNLIKELY_REENTRANCY"
    assert raw["reentrancy_detected"] is False
    assert raw["reentrancy"]["context"]["paper_profile"] is True


def test_paper_profile_ignores_reverted_opcode_writes():
    owner = "0x" + "11" * 20
    root = {"callee": owner, "caller": "0x" + "aa" * 20,
            "call_type": "CALL", "function_selector": "0xdeadbeef", "depth": 0,
            "children": []}
    write = {"address": owner, "slot": _word(1), "value_after": _word(2),
             "depth": 1, "pc": 1, "event_index": 0,
             "after_external_call": True, "reverted": True}
    raw = _extract(root, [write])
    assert raw["reentrancy_score"] == 0.0
    assert raw["reentrancy_confidence_tier"] == "NOT_REENTRANCY"


def test_paper_score_uses_activated_signals_from_opcode_adapter():
    owner = "0x" + "11" * 20
    attacker = "0x" + "22" * 20
    root = {"callee": owner, "caller": "0x" + "aa" * 20,
            "call_type": "CALL", "function_selector": "0xdeadbeef", "depth": 0,
            "children": [{"callee": attacker, "caller": owner, "call_type": "CALL",
                          "function_selector": "0x", "depth": 1, "children": [
                              {"callee": owner, "caller": attacker, "call_type": "CALL",
                               "function_selector": "0xdeadbeef", "depth": 2, "children": []}]}]}
    logs = [
        {"depth": 1, "pc": 1, "op": "SSTORE", "stack": [_word(10), _word(1)]},
        {"depth": 1, "pc": 2, "op": "CALL", "stack": [_word(0), _word(int(attacker, 16)), _word(100)]},
        {"depth": 2, "pc": 3, "op": "CALL", "stack": [_word(0), _word(int(owner, 16)), _word(100)]},
        {"depth": 3, "pc": 4, "op": "SSTORE", "stack": [_word(9), _word(1)]},
        {"depth": 1, "pc": 5, "op": "SSTORE", "stack": [_word(0), _word(1)]},
    ]
    writes = normalize_opcode_storage_trace(logs, root)["storage_events"]
    raw = _extract(root, writes)
    assert raw["reentrancy_score"] == 1.0
    assert raw["reentrancy_confidence_tier"] == "CONFIRMED_REENTRANCY"
    assert raw["debug"]["state_reentry"] is True
    assert raw["debug"]["state_changes_after_call"] is True
    assert raw["debug"]["same_function_reentered"] is True


def test_paper_structural_terms_penalty_cap_and_tiers():
    assert score_reentrancy({'same_function_reentered': True}, True) == .3375
    assert score_reentrancy({'same_contract_different_selector': True}, True) == .2625
    assert score_reentrancy({'nested_depth_reentry': True}, True) == .2625
    assert score_reentrancy({'same_function_reentered': True,
                            'same_contract_different_selector': True,
                            'nested_depth_reentry': True}, True) == .80
    assert [reentrancy_tier(score) for score in (.0, .10, .30, .55, .80)] == [
        'NOT_REENTRANCY', 'UNLIKELY_REENTRANCY', 'POSSIBLE_REENTRANCY',
        'HIGH_RISK_REENTRANCY', 'CONFIRMED_REENTRANCY']


def test_production_stage_one_activates_paper_profile(monkeypatch, tmp_path):
    from faultseeker.forensics.orchestrator import ForensicsOrchestrator
    from faultseeker.research.ablation import AblationConfig
    orchestrator = ForensicsOrchestrator(cache_dir=str(tmp_path),
        ablation=AblationConfig.disabling('faegl','tig','calibration'))
    owner = '0x'+'11'*20
    canonical = {'callee':owner,'caller':'0x'+'22'*20,'call_type':'CALL',
                 'function_selector':'0xdeadbeef','depth':0,'children':[]}
    analysis = {'trace':{},'canonical_trace':canonical,'storage_events':[],
                'flatten_trace':[],'repeated_patterns':{},'function_call_loc_memo':{},
                'function_calls_to_expand_loc':{'flashloan':[],'flashloan_callback':[],'name_in_hash':[]},
                'address_calls_with_created_contract_in_params':[]}
    monkeypatch.setattr(orchestrator.txn_sequencer,'run',lambda *a:{'chain':'eth'})
    monkeypatch.setattr(orchestrator.txn_info_collector,'run',lambda *a:{'transaction_hash':'0xexample'})
    monkeypatch.setattr('faultseeker.forensics.orchestrator.TraceAnalyzer.run',lambda self:analysis)
    monkeypatch.setattr(orchestrator.address_classifier,'run',lambda *a,**k:{
        'address_to_be_inspected':{},'potential_attacker':[],'potential_victim':[]})
    result,_,_ = orchestrator.run('0xexample','eth')
    assert result.signals['reentrancy']['context']['paper_profile'] is True


def test_complete_storage_capture_with_no_writes_does_not_activate_fallback():
    owner = '0x'+'11'*20
    canonical = {'callee':owner,'caller':'0x'+'22'*20,'call_type':'CALL',
                 'function_selector':'0xdeadbeef','depth':0,'children':[]}
    signals = SignalExtractor(txn_seq={'trace_coverage':{'storage_trace_complete':True}},
        tx_analysis={'trace':{},'canonical_trace':canonical,'storage_events':[],
                     'flatten_trace':[],'repeated_patterns':{}},paper_mode=True).run()
    assert signals.raw['reentrancy_fallback_mode'] is False
