from benchmark.detector_experiments import detector_observation, category_observation


def test_baselines_execute_different_algorithms_on_identical_captured_input():
    a, b = '0x'+'11'*20, '0x'+'22'*20
    call = {'type':'CALL','from':b,'to':a,'input':'0xdeadbeef', 'calls':[
        {'type':'CALL','from':a,'to':b,'input':'0x12345678','calls':[
            {'type':'CALL','from':b,'to':a,'input':'0xdeadbeef'}]}]}
    capture = {'raw_trace':{'call':call,'opcode':{'structLogs':[]}}}
    structural = detector_observation(capture, 'structural')
    repeated = detector_observation(capture, 'repeated')
    assert structural['predicted_exploit'] is True
    assert repeated['predicted_exploit'] is True
    assert structural['algorithm'] != repeated['algorithm']
    assert structural['input_sha256'] == repeated['input_sha256']


def test_category_observations_are_derived_from_receipt_and_actual_tree():
    trace = {'raw_trace':{'call':{'type':'CALL','from':'0xa','to':'0xb','calls':[
        {'type':'CALL','from':'0xb','to':'0xc'}]},'opcode':{'structLogs':[]}}}
    row = category_observation(trace, {'gasUsed':'0x64'}, 'access')
    assert row == {'category':'access','gas_used':100,'function_calls':2,'addresses':3,'max_depth':1}


def test_simple_baseline_counts_address_repetition_across_different_selectors():
    a,b = '0x'+'11'*20,'0x'+'22'*20
    capture = {'raw_trace':{'call':{'type':'CALL','to':a,'input':'0x11111111','calls':[
        {'type':'CALL','to':b,'input':'0x22222222','calls':[
            {'type':'CALL','to':a,'input':'0x33333333'}]}]}}}
    assert detector_observation(capture,'repeated')['predicted_exploit'] is True
