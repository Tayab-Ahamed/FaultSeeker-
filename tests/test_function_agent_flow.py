from collections import Counter
import pytest
from faultseeker.forensics.result import ForensicsResult
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.function_analysis.function_ranker import FunctionRanker
from faultseeker.data_collection.contract_downloader import ContractDownloader


@pytest.mark.parametrize('function_name',['withdraw','withdraw_funds(uint256)'])
@pytest.mark.parametrize('fail_processing',[False,True])
def test_real_function_analysis_executes_every_role_including_child_filter(monkeypatch,tmp_path,function_name,fail_processing):
    """Mock only model replies/source acquisition; run actual analysis methods."""
    owner, attacker = '0x'+'11'*20, '0x'+'22'*20
    function_key = function_name+'_'+owner
    calls, constructed = [], []
    roles = ['reasoning','generation','processing','organization','children','ranking']
    class ModelBoundary:
        def __init__(self,role):
            self.role, self.memory = role, []
        def reset_memory(self):
            self.memory.clear()
        def query(self,prompt,format='json',**kwargs):
            calls.append((self.role,prompt))
            if self.role=='processing' and fail_processing:
                raise RuntimeError('fixture provider unavailable')
            if self.role == 'children':
                return [0]
            if self.role == 'generation':
                if 'Additional information to be reorganized:' in prompt:
                    return {'children_calls':[{'function':function_name,'address':owner}]}
                return {'task_description':'Inspect child calls and source evidence','additional_information':'children calls'}
            if format == 'str':
                return 'Inspect the observed callback and storage ordering.'
            return {function_key:{'evidence':'Observed callback precedes balance write','confidence_score':.8}}
    def factory(task,model):
        role = roles[len(constructed)]
        constructed.append(role)
        return ModelBoundary(role)
    monkeypatch.setattr('faultseeker.function_analysis.function_analyzer.build_agent',factory)
    monkeypatch.setattr(ContractDownloader,'run',lambda self:{})
    child = {'type':'call','call_type':'call','function':'receive','address':attacker,
             'gas':10,'params':'','children':[]}
    root = {'type':'call','call_type':'call','function':function_name,'address':owner,
            'gas':100,'params':'','children':[child]}
    call = {'function':function_name,'address':owner,'depth':[0],'gas':100,'params':''}
    result = ForensicsResult(transaction_hash='0x'+'a'*64,chain='eth',trace=root,
        repeated_patterns={},function_call_loc_memo={function_name.lower()+'::'+owner:[call]},
        functions_to_be_inspected={'others':[call]},
        signals={'analyst_evidence':['receipt-backed note'],'attack_hypotheses':['callback hypothesis']})
    ranking = FunctionRanker().rank(result,{'repeated_patterns':{},'function_call_loc_memo':result.function_call_loc_memo})
    txn_seq = {'address_relation':{'directed':True,'multigraph':False,'graph':{},'nodes':[],'edges':[]},
               'address_calls':{},'created_address':[]}
    analyzer = FunctionAnalyzer(model='gpt-4o-mini')
    output = analyzer.run(result,txn_seq,
        {'transaction_hash':result.transaction_hash},ranking)
    if fail_processing:
        assert output['analysis_complete'] is False
        assert output['analysis_errors']
        assert output['finalized_vulnerable_functions'] == []
        from types import SimpleNamespace
        from faultseeker.core.pipeline import FaultSeekerPipeline
        from faultseeker.core.config import FaultSeekerConfig
        pipeline = FaultSeekerPipeline(FaultSeekerConfig(cache_dir=str(tmp_path)),
            forensics_orchestrator=SimpleNamespace(run=lambda *a:(result,txn_seq,{'transaction_hash':result.transaction_hash})),
            function_ranker=FunctionRanker(),function_analyzer=analyzer)
        final = pipeline.analyze_transaction(txn_hash=result.transaction_hash,chain='eth')
        assert final['analysis_complete'] is False
        assert final['analysis_errors']
        return
    assert set(role for role,_ in calls) == set(roles)
    assert output['finalized_vulnerable_functions'][0]['address'] == owner
    assert output['finalized_vulnerable_functions'][0]['confidence_score'] == [.8,.8,.8]
    summary = output['functions_to_be_inspected'][function_key]['analysis_result']['function_call_info_summary']
    assert summary['function'] == function_name
    assert summary['address'] == owner
    assert any('receipt-backed note' in prompt for role,prompt in calls if role=='organization')
    assert any('receive' in prompt for role,prompt in calls if role=='children')
