"""Software evidence-gate cases, plus a separately identified saved TRAIN replay."""
from dataclasses import fields
import json
from pathlib import Path

import pytest

from faultseeker.forensics.rule_classifier import classify
from faultseeker.forensics.signal_extractor import SignalBundle, SignalExtractor

A, B = '0x' + '11' * 20, '0x' + '22' * 20


def extract_access(calls, *, created=(), writes=(), expanded=()):
    extractor = SignalExtractor({'created_address': list(created), 'storage_events': list(writes)},
        {'flatten_trace': calls, 'function_calls_to_expand_loc': {'name_in_hash': list(expanded)}})
    extractor._check_hashed_functions()
    extractor._check_access_control()
    extractor._collate_hints()
    return extractor.signals


def test_undecoded_staticcall_is_metadata_not_write_or_unauthorized_operation():
    call = {'function': '0x12345678', 'address': A, 'call_type': 'staticcall'}
    signals = extract_access([call], expanded=[call])
    assert signals.hashed_fn_count == 1
    assert not signals.closed_source_state_change
    assert not signals.access_control_bypass
    assert classify(signals)[0] == 'UNCERTAIN'


@pytest.mark.parametrize('created', [False, True])
def test_ordinary_proxy_and_created_implementation_preserve_review_metadata(created):
    signals = extract_access([{'function': '0x12345678', 'address': A, 'call_type': 'delegatecall'}],
                             created=[A] if created else [])
    assert signals.privileged_calls[0]['type'] == ('delegatecall_into_created' if created else 'delegatecall_into_external')
    assert signals.arbitrary_external_call is created
    assert not signals.access_control_bypass
    assert classify(signals)[0] == 'UNCERTAIN'


def test_privileged_name_and_created_recipient_do_not_establish_unauthorized_access():
    signals = extract_access([{'function': 'transferownership', 'address': A,
        'call_type': 'call', 'params': B}], created=[B])
    assert signals.created_contract_in_privileged_call
    assert signals.privileged_calls[0]['type'] == 'privileged_fn'
    assert not signals.access_control_bypass
    assert classify(signals)[0] == 'UNCERTAIN'
    assert 'Access Control' not in signals.top_vuln_hints


def test_opaque_call_with_real_write_is_still_not_authorization_proof():
    call = {'function': '0x12345678', 'address': A, 'call_type': 'call'}
    signals = extract_access([call], writes=[{'address': A, 'slot': '0x1',
        'value_before': '0x0', 'value_after': '0x1', 'event_index': 0}])
    assert signals.hashed_fn_count == 1 and signals.closed_source_state_change
    assert not signals.access_control_bypass
    assert classify(signals)[0] == 'UNCERTAIN'


def test_nearby_transfer_name_does_not_prove_an_opaque_owner_write():
    signals = extract_access([
        {'function': '0x12345678', 'address': A, 'call_type': 'call'},
        {'function': 'transfer', 'address': B, 'call_type': 'call'},
    ])
    assert not signals.closed_source_state_change
    assert not signals.access_control_bypass
    assert classify(signals)[0] == 'UNCERTAIN'


def test_reverted_write_does_not_establish_opaque_owner_state_change():
    signals = extract_access([{'function': '0x12345678', 'address': A, 'call_type': 'call'}],
        writes=[{'address': A, 'slot': '0x1', 'value_before': '0x0',
                 'value_after': '0x1', 'reverted': True}])
    assert not signals.closed_source_state_change


def test_cast_selector_and_delegatecall_preserve_observations_without_auth_conclusion(tmp_path):
    path = tmp_path / 'software-cast.txt'
    path.write_text('proxy::0x12345678() [delegatecall]', encoding='utf-8')
    extractor = SignalExtractor({}, {})
    extractor._cast_cache_path = str(path)
    extractor._analyze_cast_trace_text()
    extractor._check_hashed_functions()
    extractor._check_access_control()
    assert extractor.signals.hashed_fn_count >= 1
    assert extractor.signals.privileged_calls
    assert not extractor.signals.closed_source_state_change
    assert not extractor.signals.access_control_bypass
    assert classify(extractor.signals)[0] == 'UNCERTAIN'


@pytest.mark.parametrize('weak', [
    {'closed_source_state_change': True}, {'access_control_bypass': True},
    {'created_contract_in_privileged_call': True}, {'arbitrary_external_call': True},
    {'privileged_calls': [{'type': 'privileged_fn'}]}, {'hashed_fn_count': 1},
])
def test_weak_shapes_cannot_be_exploit_or_clean_benign_even_with_complete_coverage(weak):
    signals = SignalBundle(**weak, raw={'coverage': {'trace_complete': True,
        'token_flow_complete': True, 'multi_tx_context_complete': True}})
    assert classify(signals)[0] == 'UNCERTAIN'


def test_saved_real_train_signals_choose_storage_reentrancy_instead_of_opacity():
    # Actual cached signal replay, not a new production run or ground-truth input.
    root = Path(__file__).resolve().parents[1]
    paths = list((root / 'reports/cohort_rebuild_v2/gateway_runs/20261016T112421-02f4bcc2').glob('eth-*/forensics/*.json'))
    report = json.loads(paths[0].read_text(encoding='utf-8'))['classification']
    assert report['matched_rule'] == 'closed_source_access_control'
    saved = report['signals']
    assert saved['reentrancy_context']['storage_trace_available'] is True
    assert saved['debug']['storage_events_total'] == 106
    assert saved['reentrancy_score'] == 1.0 and saved['profit_extraction_eth'] == 0
    supported = {field.name for field in fields(SignalBundle)}
    signals = SignalBundle(**{key: value for key, value in saved.items() if key in supported})
    verdict, confidence, rule, hint = classify(signals)
    assert (verdict, confidence, rule, hint) == ('EXPLOIT', .75, 'reentrancy_pattern', 'Reentrancy')


@pytest.mark.parametrize('score,profit,rule,confidence', [
    (.85, .51, 'reentrancy_with_profit', .92),
    (.45, 0, 'reentrancy_pattern', .75),
])
def test_existing_reentrancy_thresholds_are_preserved(score, profit, rule, confidence):
    signals = SignalBundle(reentrancy_score=score, profit_extraction_eth=profit,
                           closed_source_state_change=True)
    assert classify(signals)[:3] == ('EXPLOIT', confidence, rule)
