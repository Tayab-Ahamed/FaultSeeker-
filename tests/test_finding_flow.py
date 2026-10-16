"""Observed model findings and returned ordering must govern final output."""
import sys
sys.modules['readline']=None
from copy import deepcopy
from types import SimpleNamespace
import pytest
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
A='0x'+'11'*20
B='0x'+'22'*20
KNOWN='foo_'+A
OTHER='bar_'+B

def analyzer(response):
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace(query=lambda *args,**kw:response))
 a.tx_analysis={'function_call_loc_memo':{'foo::'+A:[{'depth':[0]}],'bar::'+B:[{'depth':[0,1,0]}]}}
 a.current_task={};a.processing_result='actual model analysis';a.understanding_result='context';a.cheatsheet=[]
 return a

def test_unobserved_model_finding_is_rejected_before_any_mutation():
 response={KNOWN:{'evidence':'Observed source candidate','confidence_score':.5},'invented_'+B:{'evidence':'Unobserved candidate','confidence_score':.9}}
 a=analyzer(response)
 with pytest.raises(ValueError):a._update_potentially_vulnerable_function()
 assert a.potentially_vulnerable_functions=={}

@pytest.mark.parametrize('score',[True,float('nan'),float('inf'),-0.1,1.1,'0.9'])
def test_invalid_confidence_is_rejected_without_partial_findings(score):
 a=analyzer({KNOWN:{'evidence':'Source candidate','confidence_score':score}})
 with pytest.raises(ValueError):a._update_potentially_vulnerable_function()
 assert a.potentially_vulnerable_functions=={}

def test_zero_confidence_is_preserved_as_reported():
 a=analyzer({KNOWN:{'evidence':'Uncertain candidate','confidence_score':0.0}})
 a._update_potentially_vulnerable_function()
 assert a.potentially_vulnerable_functions[KNOWN]['confidence_score']==[0.0]

def test_model_order_is_used_and_shallow_candidates_are_not_discarded():
 a=analyzer([KNOWN,OTHER])
 a.potentially_vulnerable_functions={OTHER:{'evidence':['deep'],'confidence_score':[.8],'depth':3},KNOWN:{'evidence':['shallow'],'confidence_score':[.7],'depth':1}}
 before=deepcopy(a.potentially_vulnerable_functions)
 a._rank_potentially_vulnerable_functions()
 output=a._finalize_potentially_vulnerable_functions()
 assert [(row['function'],row['address']) for row in output]==[('foo',A),('bar',B)]
 assert [row['model_rank'] for row in output]==[1,2]
 assert a.potentially_vulnerable_functions==before

@pytest.mark.parametrize('response',[[KNOWN], [KNOWN,KNOWN], [KNOWN,OTHER,'invented_'+A],{KNOWN:1},None])
def test_ranking_rejects_missing_duplicate_or_unsupported_identities(response):
 a=analyzer(response)
 a.potentially_vulnerable_functions={KNOWN:{'evidence':['x'],'confidence_score':[.7],'depth':1},OTHER:{'evidence':['y'],'confidence_score':[.8],'depth':3}}
 with pytest.raises(ValueError):a._rank_potentially_vulnerable_functions()

def test_all_validated_candidates_reach_real_stage_three_scorer():
 from faultseeker.core.confidence_scorer import ConfidenceScorer
 a=analyzer([KNOWN,OTHER])
 a.potentially_vulnerable_functions={OTHER:{'evidence':['Observed deeper candidate'],'confidence_score':[.8],'depth':3},KNOWN:{'evidence':['Observed shallower candidate'],'confidence_score':[.7],'depth':1}}
 a._rank_potentially_vulnerable_functions()
 scored=ConfidenceScorer().score_all(a._finalize_potentially_vulnerable_functions(),{'repeated_patterns':{},'balance_change':{},'potential_attacker':[],'potential_victim':[]})
 assert {(row['function'],row['address']) for row in scored}=={('foo',A),('bar',B)}
 assert all('components' in row['confidence'] for row in scored)


def test_actual_analysis_loop_records_unobserved_finding_and_invokes_stop_policy():
 from benchmark.nara_pilot_provider import StudyStop
 calls=[]
 def factory(task,role):
  def query(prompt,format='json'):
   calls.append((role,format))
   if role=='generation_agent':
    if 'Additional information to be reorganized:' in prompt:return {}
    return {'task_description':'Inspect observed source','additional_information':''}
   if format=='str':return 'Observed context.'
   if role=='organization_agent':return {'invented_'+B:{'evidence':'Unobserved model claim','confidence_score':.9}}
   raise AssertionError('Unexpected model role')
  return SimpleNamespace(query=query)
 def stop(error):raise StudyStop('Stop after '+type(error).__name__)
 a=FunctionAnalyzer(agent_factory=factory,analysis_error_handler=stop)
 a.function_call_info_summary={'function':'foo','address':A}
 a.tx_analysis={'function_call_loc_memo':{'foo::'+A:[{'depth':[0]}]}}
 a.cheatsheet=[]
 with pytest.raises(StudyStop):a._function_analysis_init()
 assert a.potentially_vulnerable_functions=={}
 assert a.analysis_errors==[{'error_type':'ValueError','function':'foo','address':A}]
 assert calls[-1]==('organization_agent','json')
