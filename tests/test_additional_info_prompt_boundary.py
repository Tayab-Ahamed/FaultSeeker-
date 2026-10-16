"""Schema instructions follow the potentially large public call/source context."""
import sys
sys.modules['readline']=None
from types import SimpleNamespace
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer


def test_additional_info_schema_is_explicit_after_current_information():
    prompts=[]
    analyzer=FunctionAnalyzer(agent_factory=lambda *a,**k:SimpleNamespace())
    analyzer.generation_agent=SimpleNamespace(query=lambda prompt:prompts.append(prompt) or {})
    analyzer.function_prompts=SimpleNamespace(retrieve_additional_info='SCHEMA-INSTRUCTIONS')
    analyzer.function_call_info_summary={'context':'PUBLIC-CONTEXT'*1000}
    assert analyzer._retrieve_additional_info('CURRENT-TASK')=={}
    prompt=prompts[0]
    assert prompt.rstrip().endswith('SCHEMA-INSTRUCTIONS')
    assert prompt.index('CURRENT-TASK')<prompt.rfind('SCHEMA-INSTRUCTIONS')


def test_schema_prompts_distinguish_function_selector_from_address():
    from faultseeker.prompts.function_analysis.worker_prompts import WorkerPrompts
    from faultseeker.prompts.local_model_prompts import LocalWorkerPrompts
    for prompts in (WorkerPrompts(),LocalWorkerPrompts()):
        text=prompts.retrieve_additional_info
        assert 'function_call (singular)' in text
        assert 'selector is not an address' in text
        assert 'observed_entry_functions_at_address' in text
        assert 'observed_child_calls' in text


def test_related_info_exposes_observed_identity_catalog():
    import networkx as nx
    owner='0x'+'11'*20
    child='0x'+'22'*20
    analyzer=FunctionAnalyzer(agent_factory=lambda *a,**k:SimpleNamespace())
    analyzer.fundflow_analysis={'balance_change':{}}
    analyzer.txn_seq={'address_calls':{owner:['0x12345678']}}
    analyzer.trace=[{'address':owner,'function':'0x12345678','children':[
        {'address':child,'function':'0x87654321','call_type':'delegatecall'}]}]
    analyzer.address_relation=nx.DiGraph()
    analyzer._retrieve_source_code=lambda *a:[]
    result=analyzer._retrieve_related_info(owner,'0x12345678')
    assert 'address_calls' not in result
    assert result['observed_entry_functions_at_address']==[
        {'address':owner,'function':'0x12345678'}]
    assert result['observed_child_calls'][0]['address']==child
    assert result['observed_child_calls'][0]['function']=='0x87654321'
    assert result['observed_child_calls'][0]['call_type']=='delegatecall'
