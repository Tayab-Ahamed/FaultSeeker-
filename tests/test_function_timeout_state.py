"""Regression tests: synthetic provider/clock boundaries, no empirical claims."""
import sys
sys.modules['readline']=None
from collections import Counter
from types import SimpleNamespace
import pytest
from benchmark.nara_pilot_provider import StudyStop
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.function_analysis.function_ranker import RankingResult
from faultseeker.forensics.result import ForensicsResult

A='0x'+'11'*20


def make_analyzer(monkeypatch,exit_kind,callback=None,cloud=True,adequacy='yes'):
    calls=Counter()
    class Agent:
        def __init__(self,role):self.role=role
        def reset_memory(self):pass
        def query(self,prompt,format='json',**kwargs):
            calls[self.role]+=1
            if self.role=='generation_agent':
                if exit_kind=='empty':return {}
                if 'Additional information to be reorganized:' in prompt:return {}
                return {'task_description':'Inspect observed trace','additional_information':''}
            if self.role=='organization_agent':return adequacy if format=='str' else {}
            if format=='str':return 'Inspect the recorded operation.'
            return []
    a=FunctionAnalyzer(model='gpt-4o-mini' if cloud else 'fixture-local',
        agent_factory=lambda task,role:Agent(role),
        contract_downloader_factory=lambda *args:SimpleNamespace(run=lambda:{}),
        analysis_error_handler=callback)
    a.function_call_info_summary={'function':'foo','address':A,'calls':[]}
    a.cheatsheet=[]
    a.tx_analysis={'function_call_loc_memo':{'foo::'+A:[{'depth':[0]}]}}
    # The real loops and real task selection run unchanged. A deterministic
    # clock expires after fn_start, never by sleeping or altering thresholds.
    ticking={'armed':False,'reads':0}
    def clock():
        if not ticking['armed']:return 0.0
        ticking['reads']+=1
        return 0.0 if ticking['reads']==1 else 481.0
    def uses_cloud():
        if exit_kind=='wall':ticking.update(armed=True,reads=0)
        return cloud
    monkeypatch.setattr(a,'_uses_cloud_model',uses_cloud)
    monkeypatch.setattr('time.time',clock)
    return a,calls


@pytest.mark.parametrize('method',['_function_analysis_init','_txn_analysis_init'])
@pytest.mark.parametrize('exit_kind',['wall','empty'])
def test_abort_records_safe_timeout(monkeypatch,method,exit_kind):
    a,calls=make_analyzer(monkeypatch,exit_kind)
    getattr(a,method)()
    assert a.analysis_errors==[{'error_type':'TimeoutError','function':'foo','address':A}]
    assert calls['processing_agent']==0
    assert calls['generation_agent']==(0 if exit_kind=='wall' else 2)


@pytest.mark.parametrize('method',['_function_analysis_init','_txn_analysis_init'])
@pytest.mark.parametrize('exit_kind',['wall','empty'])
def test_timeout_callback_receives_error_and_stops_next_task(monkeypatch,method,exit_kind):
    observed=[]
    def callback(error):
        observed.append(error)
        raise StudyStop('synthetic domain stop')
    a,calls=make_analyzer(monkeypatch,exit_kind,callback)
    with pytest.raises(StudyStop):getattr(a,method)()
    assert len(observed)==1 and isinstance(observed[0],TimeoutError)
    assert a.analysis_errors[0]['error_type']=='TimeoutError'
    assert calls['processing_agent']==0
    assert calls['generation_agent']==(0 if exit_kind=='wall' else 2)


@pytest.mark.parametrize('exit_kind',['wall','empty'])
def test_actual_run_reports_incomplete_after_actual_function_loop(monkeypatch,exit_kind):
    a,_=make_analyzer(monkeypatch,exit_kind)
    call={'function':'foo','address':A,'gas':100,'params':'','depth':[0]}
    trace={'type':'call','call_type':'call','function':'foo','address':A,'gas':100,'params':'','children':[]}
    result=ForensicsResult(transaction_hash='0x'+'a'*64,chain='eth',trace=trace,
        repeated_patterns={},function_call_loc_memo={'foo::'+A:[call]},functions_to_be_inspected={'others':[call]})
    ranking=RankingResult(functions_to_be_inspected={'foo_'+A:{'count':1,'calls':[call]}},address_list=[A])
    seq={'address_relation':{'directed':True,'multigraph':False,'graph':{},'nodes':[],'edges':[]},'address_calls':{},'created_address':[]}
    output=a.run(result,seq,{'transaction_hash':result.transaction_hash},ranking)
    assert output['analysis_complete'] is False
    assert output['analysis_errors']==[{'error_type':'TimeoutError','function':'foo','address':A}]


@pytest.mark.parametrize('method,expected',[('_function_analysis_init',2),('_txn_analysis_init',2)])
def test_normal_adequacy_exit_remains_complete(monkeypatch,method,expected):
    a,calls=make_analyzer(monkeypatch,'normal',adequacy='yes')
    getattr(a,method)()
    assert a.analysis_errors==[]
    assert calls['processing_agent']==expected


@pytest.mark.parametrize('method,cloud,expected',[
    ('_function_analysis_init',True,3),('_function_analysis_init',False,8),
    ('_txn_analysis_init',True,2),('_txn_analysis_init',False,3)])
def test_existing_iteration_policy_is_unchanged(monkeypatch,method,cloud,expected):
    a,calls=make_analyzer(monkeypatch,'normal',cloud=cloud,adequacy='not sufficient')
    getattr(a,method)()
    assert a.analysis_errors==[]
    assert calls['processing_agent']==expected
