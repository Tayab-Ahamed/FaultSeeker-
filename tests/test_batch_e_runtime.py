from copy import deepcopy
from scripts.research.score_batch_e import DecodedSequencer
from faultseeker.utils.rpc_provider import normalize_trace_node


def test_generic_names_keep_canonical_literal_selector_and_original_capture():
    raw={'type':'CALL','from':'0x'+'1'*40,'to':'0x'+'2'*40,'input':'0xa9059cbb'+'0'*128,'output':'0x','gas':'0x10000','gasUsed':'0x100','value':'0x0','calls':[]}
    before=deepcopy(raw)
    structured={'transaction_hash':'0x'+'3'*64,'chain':'eth','trace':normalize_trace_node(raw),'trace_coverage':{'trace_complete':True}}
    names={'0xa9059cbb':{'decoded_name':'transfer','verified_abi':False}}
    observed=DecodedSequencer(structured,names).run(structured['transaction_hash'],'eth')
    assert observed['trace']['function']=='transfer'
    assert observed['trace']['runtime_selector']=='0xa9059cbb'
    assert observed['canonical_trace']['function_selector']=='0xa9059cbb'
    assert raw==before


def test_unknown_registry_name_remains_literal():
    raw={'type':'CALL','from':'0x'+'1'*40,'to':'0x'+'2'*40,'input':'0x12345678','gas':'0x10000','value':'0x0','calls':[]}
    structured={'transaction_hash':'0x'+'3'*64,'chain':'eth','trace':normalize_trace_node(raw)}
    observed=DecodedSequencer(structured,{}).run(structured['transaction_hash'],'eth')
    assert observed['trace']['function']=='0x12345678'


def test_inference_guard_blocks_provider_dispatch():
    import pytest
    from scripts.research.score_batch_e import inference_guard
    for event in ('socket.connect','socket.getaddrinfo','http.client.connect','subprocess.Popen'):
        with pytest.raises(RuntimeError):inference_guard(event,())
    inference_guard('open',())
