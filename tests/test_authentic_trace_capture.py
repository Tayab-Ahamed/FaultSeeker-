import pytest


def test_complexity_counts_unique_contract_and_selector_pairs_not_transfers_or_repeats():
    from scripts.capture_authentic_traces import complexity_observation
    a,b,eoa='0x'+'a'*40,'0x'+'b'*40,'0x'+'c'*40
    trace={'to':a,'input':'0x12345678','calls':[
        {'to':a,'input':'0x12345678'}, {'to':b,'input':'0x12345678'},
        {'to':eoa,'input':'0x'}]}
    result=complexity_observation(trace,{a:'0x6000',b:'0x6000',eoa:'0x'})
    assert result['unique_function_calls']==2
    assert result['trace_frames']==4
    assert result['complexity_class']=='Simple'
    with pytest.raises(ValueError,match='code'):
        complexity_observation(trace,{a:'0x6000'})


def test_call_trace_identity_must_match_resolved_transaction():
    from scripts.capture_authentic_traces import validate_call_identity
    with pytest.raises(ValueError):
        validate_call_identity({'from':'0xa','to':'0xb'},{'from':'0xa','to':'0xc'})


def test_contract_creation_trace_binds_receipt_contract_address():
    from scripts.capture_authentic_traces import validate_call_identity
    transaction={'from':'0xa','to':None}
    trace={'from':'0xa','to':'0xb','type':'CREATE'}
    validate_call_identity(trace,transaction,{'contractAddress':'0xb'})
    with pytest.raises(ValueError):
        validate_call_identity(trace,transaction,{'contractAddress':'0xc'})


def test_destroyed_contract_cannot_be_mistaken_for_eoa_in_complexity_count():
    from scripts.capture_authentic_traces import complexity_observation
    trace={'to':'0xa','input':'0x12345678','calls':[{'to':'0xb','input':'0x'}]}
    with pytest.raises(ValueError,match='code'):
        complexity_observation(trace,{'0xa':'0x','0xb':'0x'})


def test_prestate_code_recovers_destroyed_contract_without_inventing_storage_events():
    from scripts.capture_authentic_prestate import enrich_capture
    capture={'raw_trace':{'call':{'from':'0xf','to':'0x'+'a'*40,'input':'0x12345678','calls':[{'to':'0x'+'b'*40,'input':'0x'}]}},
             'historical_code':{'0x'+'a'*40:'0x','0x'+'b'*40:None},'storage_trace_complete':False}
    out=enrich_capture(capture,{'0x'+'a'*40:{'code':'0x6000'},'0x'+'b'*40:{'balance':'0x1'}})
    assert out['historical_code']=={'0x'+'a'*40:'0x6000','0x'+'b'*40:'0x'}
    assert out['complexity']['unique_function_calls']==1
    assert not out['storage_trace_complete']
    assert 'opcode' not in out['raw_trace']


def test_prestate_account_map_rejects_non_address_keys():
    from scripts.capture_authentic_prestate import enrich_capture
    with pytest.raises(ValueError,match='account map'):
        enrich_capture({}, {'not-a-chain-address':{'code':'0x6000'}})
