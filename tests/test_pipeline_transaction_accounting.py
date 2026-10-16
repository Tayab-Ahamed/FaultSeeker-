"""Software-only shared-router accounting regression; no empirical evidence."""
import sys
sys.modules['readline']=None
from types import SimpleNamespace
from benchmark.captured_inputs import load_train_inputs
from scripts.run_train_gateway_pilot import ROOT, MODEL
from scripts.run_train_production import no_network
from faultseeker.core.config import FaultSeekerConfig
from faultseeker.core.pipeline import FaultSeekerPipeline
from faultseeker.core.llm_router import HybridLLMRouter, COST_RATES
from faultseeker.core.confidence_scorer import DEFAULT_WEIGHTS
from faultseeker.function_analysis.function_ranker import FunctionRanker

KEY='eth:0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'


def test_two_actual_pipeline_cases_share_router_without_double_counting(tmp_path,monkeypatch):
    monkeypatch.setitem(COST_RATES,MODEL,{'input':1,'output':2})
    router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',remote_model_ids={MODEL})
    inputs=load_train_inputs(ROOT,KEY)
    calls=[]
    finding={'function':'0x12345678','address':'0x'+'11'*20,'evidence':'recursive callback reentrancy','confidence_score':[.8]}
    def analyze(*args):
        n=len(calls)+1
        router.record_query(model=MODEL,tier=3,prompt_length=0,response_length=0,
                           input_tokens=n*100,output_tokens=n*10,usage_source='observed',duration_ms=n)
        calls.append(n)
        return {'analysis_complete':True,'finalized_vulnerable_functions':[finding],
                'potentially_vulnerable_functions':[finding]}
    config=FaultSeekerConfig(auto_route=False,human_in_loop=False,track_cost=True,calibration_model_path='',output_dir=str(tmp_path))
    pipeline=FaultSeekerPipeline(config,forensics_orchestrator=inputs.orchestrator(tmp_path/'forensics'),
                                function_ranker=FunctionRanker(),function_analyzer=SimpleNamespace(run=analyze))
    pipeline.router=router
    with no_network():
        first=pipeline.analyze_transaction(txn_hash=inputs.structured['transaction_hash'],chain='eth')
        second=pipeline.analyze_transaction(txn_hash=inputs.structured['transaction_hash'],chain='eth')
    assert first['query_records'][0]['input_tokens_est']==100
    assert len(first['query_records'])==len(second['query_records'])==1
    assert second['query_records'][0]['input_tokens_est']==200
    assert abs(first['llm_cost']-.00012)<1e-10
    assert abs(second['llm_cost']-.00024)<1e-10
    assert first['cost_summary']['total_queries']==second['cost_summary']['total_queries']==1
    assert second['cost_summary']['cloud_queries']==1
    assert second['router_cumulative_cost_summary']['total_queries']==2
    assert abs(second['router_cumulative_cost_summary']['total_cost_usd']-.00036)<1e-10
    assert first['query_records'][0]['input_tokens_est']==100
    for result in [first,second]:
        confidence=result['scored_functions'][0]['confidence']
        assert abs(confidence['overall']-sum(DEFAULT_WEIGHTS[k]*confidence['components'][k] for k in DEFAULT_WEIGHTS))<.0002


def test_benign_bypass_excludes_existing_router_history(tmp_path,monkeypatch):
    monkeypatch.setitem(COST_RATES,MODEL,{'input':1,'output':2})
    router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',remote_model_ids={MODEL})
    router.record_query(model=MODEL,tier=3,prompt_length=0,response_length=0,input_tokens=100,output_tokens=10,usage_source='observed')
    inputs=load_train_inputs(ROOT,KEY)
    actual=inputs.orchestrator(tmp_path/'forensics')
    def run(*args):
        result,sequence,info=actual.run(*args)
        result.rule_verdict='BENIGN'
        result.rule_confidence=.95
        return result,sequence,info
    def forbidden(*args):raise AssertionError('BENIGN bypass invoked Stage2')
    pipeline=FaultSeekerPipeline(FaultSeekerConfig(auto_route=False,human_in_loop=False,track_cost=True,output_dir=str(tmp_path)),
        forensics_orchestrator=SimpleNamespace(run=run,txn_sequencer=actual.txn_sequencer),function_analyzer=SimpleNamespace(run=forbidden))
    pipeline.router=router
    with no_network():
        result=pipeline.analyze_transaction(txn_hash=inputs.structured['transaction_hash'],chain='eth')
    assert result['stage2_bypassed'] is True
    assert result['query_records']==[] and result['llm_cost']==0
    assert result['cost_summary']['total_queries']==0
    assert result['cost_summary']['total_cost_usd']==0
    assert result['router_cumulative_cost_summary']['total_queries']==1


def test_accounting_refuses_rewritten_prior_observations():
    import pytest
    prior={'total_cost_usd':.01,'records':[{'cost_usd':.01,'model':'original'}]}
    router=SimpleNamespace(get_cost_summary=lambda:{'total_cost_usd':.02,'records':[{'cost_usd':.02,'model':'changed'}]})
    pipeline=FaultSeekerPipeline(FaultSeekerConfig(track_cost=True))
    pipeline.router=router
    with pytest.raises(ValueError,match='history changed'):
        pipeline._attach_transaction_cost({},prior)
