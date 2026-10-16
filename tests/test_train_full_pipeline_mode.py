"""Software-only full-pipeline wiring tests, never empirical claim evidence."""
import socket
import sys
from types import SimpleNamespace
sys.modules['readline']=None
import pytest
from scripts import run_train_gateway_pilot as runner
from benchmark.captured_inputs import load_train_inputs
from faultseeker.core.confidence_scorer import ConfidenceScorer, DEFAULT_WEIGHTS

IDENTITY='eth:0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'


def test_actual_pipeline_scores_eq4_and_keeps_actual_router_records(tmp_path, monkeypatch):
    inputs=load_train_inputs(runner.ROOT,IDENTITY)
    expected_queries=[{'model':'software-fixture','cost_usd':.012,'usage_source':'observed','tier':3}]
    recorded=[]
    router=SimpleNamespace(get_cost_summary=lambda:{'total_cost_usd':.012 if recorded else 0,'records':recorded},print_cost_report=lambda:None)
    finding={'function':'0x12345678','address':'0x'+'11'*20,'evidence':'recursive reentrancy callback with missing state update','confidence_score':[.7]}
    analysis_calls=[]
    def analyze(*args):
        analysis_calls.append(args)
        recorded.extend(expected_queries)
        return {'analysis_complete':True,'analysis_errors':[], 'finalized_vulnerable_functions':[finding],
                'potentially_vulnerable_functions':[finding],'ranked_result':[], 'transaction_understanding':'software fixture'}
    analyzer=SimpleNamespace(run=analyze)
    original=ConfidenceScorer.score_all
    scored=[]
    def score(self,functions,forensics):
        scored.append(functions)
        return original(self,functions,forensics)
    monkeypatch.setattr(ConfidenceScorer,'score_all',score)
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('Unexpected parent network'))
    result=runner.execute_full_pipeline(inputs,analyzer,router,tmp_path)
    assert len(analysis_calls)==1 and scored==[[finding]]
    assert result['analysis_complete'] is True
    assert result['query_records']==expected_queries and result['llm_cost']==.012
    assert len(result['scored_functions'])==1 and len(result['evidence_cards'])==1
    confidence=result['scored_functions'][0]['confidence']
    weighted=sum(DEFAULT_WEIGHTS[k]*confidence['components'][k] for k in DEFAULT_WEIGHTS)
    assert abs(confidence['overall']-weighted)<.0002
    assert confidence['score_semantics']=='heuristic-relative-ranking'


def test_full_pipeline_error_propagates_without_fabricating_output(tmp_path):
    inputs=load_train_inputs(runner.ROOT,IDENTITY)
    def fail(*a):raise RuntimeError('Software analysis failure')
    with pytest.raises(RuntimeError,match='Software analysis failure'):
        runner.execute_full_pipeline(inputs,SimpleNamespace(run=fail),SimpleNamespace(get_cost_summary=lambda:{}),tmp_path)


def test_empty_completed_output_has_no_invented_stage3_measurement(tmp_path):
    inputs=load_train_inputs(runner.ROOT,IDENTITY)
    analyzer=SimpleNamespace(run=lambda *a:{'analysis_complete':True,'analysis_errors':[], 'finalized_vulnerable_functions':[], 'potentially_vulnerable_functions':[]})
    router=SimpleNamespace(get_cost_summary=lambda:{'total_cost_usd':0,'records':[]},print_cost_report=lambda:None)
    result=runner.execute_full_pipeline(inputs,analyzer,router,tmp_path)
    assert result['analysis_complete'] is True
    assert result['scored_functions']==[] and result['evidence_cards']==[]


def test_full_pipeline_cli_is_optional_and_explicit(monkeypatch):
    calls=[]
    monkeypatch.setattr(runner,'run',lambda **kw:calls.append(kw))
    runner.main(['--live','--full-pipeline','--identity',IDENTITY])
    assert calls[0]['full_pipeline'] is True
    assert calls[0]['requested_ids']==[IDENTITY]



def test_unexpected_parent_network_is_terminal_even_if_pipeline_swallows_it(tmp_path):
    inputs=load_train_inputs(runner.ROOT,IDENTITY)
    def analyze(*args):
        try:
            socket.socket().connect(('example.invalid',443))
        except RuntimeError:
            pass
        return {'analysis_complete':True,'finalized_vulnerable_functions':[]}
    router=SimpleNamespace(get_cost_summary=lambda:{'total_cost_usd':0,'records':[]},print_cost_report=lambda:None)
    with pytest.raises(RuntimeError,match='Unexpected parent network'):
        runner.execute_full_pipeline(inputs,SimpleNamespace(run=analyze),router,tmp_path)


@pytest.mark.parametrize('failure', [False, True])
def test_full_mode_run_logs_actual_stage_coverage_and_stops_errors(tmp_path, monkeypatch, failure):
    from pathlib import Path
    from benchmark.research_protocol import write_json
    other='eth:0x'+'a'*64
    protocol={'train_identities':[IDENTITY,other],'seed':1729,'experiment':'software-only','source_inputs':{}}
    base=tmp_path/runner.BASE
    write_json(base/'provider_pilot/protocol.json',protocol)
    write_json(base/'provider_pilot/approval.json',{})
    write_json(tmp_path/'benchmark/eval_split.json',{'status':'FROZEN','train_ids':[IDENTITY,other]})
    monkeypatch.setattr(runner,'configuration',lambda root:(protocol,{'input':1,'output':1}))
    monkeypatch.setattr(runner,'approved_call_cap',lambda *a:20)
    monkeypatch.setattr(runner,'approved_budget_limit',lambda *a:10)
    class Guard:
        def __init__(self,*a,**kw):pass
        def report(self):return {'spent_usd':0}
    monkeypatch.setattr(runner,'SpendGuard',Guard)
    monkeypatch.setattr(runner,'system_identity',lambda *a:{})
    def snapshot(system,out):
        path=out/'snapshot.json';write_json(path,{});return path
    monkeypatch.setattr(runner,'snapshot_system',snapshot)
    records=[{'model':'software','cost_usd':.01,'usage_source':'observed'}]
    recorded=[]
    router=SimpleNamespace(get_cost_summary=lambda:{'total_cost_usd':.01 if recorded else 0,'records':recorded},print_cost_report=lambda:None)
    monkeypatch.setattr(runner,'HybridLLMRouter',lambda **kw:router)
    monkeypatch.setattr('dotenv.dotenv_values',lambda path:{'BYNARA_API_KEY':'software-key'})
    exists=Path.exists
    monkeypatch.setattr(Path,'exists',lambda path:True if path.name=='.env' else exists(path))
    class Pilot:
        calls=0
        stop_reason=''
        factory=None
        stop_after_analysis_error=None
        def __init__(self,**kw):pass
    monkeypatch.setattr(runner,'NaraPilot',Pilot)
    real_inputs=load_train_inputs(runner.ROOT,IDENTITY)
    loaded=[]
    def inputs(root,key,require_opcodes=True):
        loaded.append(key)
        return real_inputs
    monkeypatch.setattr(runner,'load_train_inputs',inputs)
    monkeypatch.setattr(runner.VerifiedSourceDownloader,'factory',lambda **kw:None)
    def analyze(*a):
        if failure:raise RuntimeError('Deliberate software error')
        recorded.extend(records)
        return {'analysis_complete':True,'analysis_errors':[], 'finalized_vulnerable_functions':[], 'potentially_vulnerable_functions':[]}
    monkeypatch.setattr(runner,'FunctionAnalyzer',lambda **kw:SimpleNamespace(run=analyze))
    monkeypatch.setattr(runner,'append_experiment',lambda *a:None)
    requested=[IDENTITY,other] if failure else [IDENTITY]
    report=runner.run(tmp_path,live=True,requested_ids=requested,full_pipeline=True)
    assert loaded==[IDENTITY]
    assert report['config']['execution_mode']==report['execution_mode']=='full-production-pipeline'
    assert report['metrics'] is None
    if failure:
        assert report['complete_cases']==0
        assert report['stop_reason']=='Production pilot failed: RuntimeError'
    else:
        assert report['complete_cases']==1
        observation=report['observations'][0]
        assert observation['complete'] is True
        assert observation['stage2_bypassed'] is False and observation['analysis_errors']==[]
        assert observation['stage3_score_count']==0
        import json
        payload=json.loads((tmp_path/observation['artifact']['path']).read_text())
        assert payload['production_output']['query_records']==records
        assert payload['production_output']['scored_functions']==[]
