from faultseeker.forensics.signal_extractor import SignalExtractor


def test_three_structural_signals_fire_without_storage_and_are_penalized_and_capped():
    owner,other = '0x'+'11'*20,'0x'+'22'*20
    def node(address,selector,depth,children):
        return {'callee':address,'caller':other if address==owner else owner,
                'call_type':'CALL','function_selector':selector,'depth':depth,'children':children}
    root = node(owner,'0x11111111',0,[node(other,'0x22222222',1,[
        node(owner,'0x33333333',2,[node(other,'0x22222222',3,[node(owner,'0x11111111',4,[])])])])])
    output = SignalExtractor(txn_seq={},tx_analysis={'trace':{},'canonical_trace':root,
        'storage_events':[],'flatten_trace':[],'repeated_patterns':{}},paper_mode=True).run().raw
    assert output['reentrancy_fallback_mode'] is True
    assert output['debug']['same_function_reentered'] is True
    assert output['debug']['same_contract_different_selector'] is True
    assert output['debug']['nested_depth_reentry'] is True
    assert output['reentrancy_score'] == .8
