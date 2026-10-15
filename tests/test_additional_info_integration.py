"""Production evidence lookups reject malformed model requests atomically."""
import sys
sys.modules['readline']=None
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
A='0x'+'11'*20
B='0x'+'22'*20

def analyzer(request):
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace(query=lambda *a,**k:request))
 a.function_call_info_summary={'high_appearance_count_children_calls':{'foo::'+A:1,'foo::'+B:1}}
 a.fundflow_analysis={'balance_change':{A:{'ETH':1}}}
 calls=[]
 a._retrieve_function_calls=lambda ref:calls.append(('call',ref)) or [ref]
 a._retrieve_children_calls=lambda fn,address:calls.append(('child',fn,address)) or [fn]
 a._retrieve_source_code=lambda address,fn:calls.append(('source',fn,address)) or ['source']
 return a,calls

def test_documented_pair_order_and_requested_source_owner_are_preserved():
 a,calls=analyzer({'function_call':[[A,'foo']],'children_calls':[[A,'foo']],'source_code':[[A,'foo']]})
 a._retrieve_additional_info('request')
 assert calls==[('call',{'address':A,'function':'foo'}),('child','foo',A),('source','foo',A)]

@pytest.mark.parametrize('payload',[
 {'function_call':[[A,'foo']],'children_calls':['callInternalModule::moduleLookup']},
 {'function_call':[[A,'foo']],'balance_change':['0x123']},
 {'source_code':['foo::moduleLookup']},
])
def test_bad_reference_rejects_every_lookup_before_io(payload):
 a,calls=analyzer(payload)
 with pytest.raises(ValueError):a._retrieve_additional_info('request')
 assert calls==[]

def test_actual_saved_response_is_rejected_before_any_lookup():
 p=Path(__file__).resolve().parents[1]/'reports/cohort_rebuild_v2/gateway_runs/20261015T180644-7cc259e6/calls/call-005.json'
 raw=json.loads(p.read_text())['response']['choices'][0]['message']['content']
 a,calls=analyzer(json.loads(raw.split('```json')[1].split('```')[0]))
 with pytest.raises(ValueError):a._retrieve_additional_info('request')
 assert calls==[]

def test_valid_unambiguous_string_refs_use_full_owner():
 a,calls=analyzer({'children_calls':['foo::'+A],'source_code':[A+'::foo']})
 a._retrieve_additional_info('request')
 assert calls==[('child','foo',A),('source','foo',A)]

def test_optional_error_policy_records_error_then_stops_without_raw_exception_text():
 class Stop(BaseException):pass
 def handler(error):
  assert isinstance(error,ValueError)
  raise Stop('domain error')
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace(),analysis_error_handler=handler)
 with pytest.raises(Stop):a._record_analysis_error(ValueError('secret-like-sentinel'))
 assert a.analysis_errors==[{'error_type':'ValueError','function':'','address':''}]
 assert 'secret-like-sentinel' not in str(a.analysis_errors)


def test_valid_early_reference_plus_invalid_late_source_rejects_every_lookup():
 a,calls=analyzer({'function_call':[[A,'foo']],'children_calls':[[A,'foo']],
                  'source_code':[['moduleLookup','implementation']]})
 with pytest.raises(ValueError):a._retrieve_additional_info('request')
 assert calls==[]


def test_mixed_case_addresses_and_legacy_source_dictionary_are_canonical_before_io():
 owner='0x'+'Ab'*20
 a,calls=analyzer({'function_call':[[owner,'foo']], 'children_calls':['foo::'+owner],
                  'source_code':{'function_name':'foo','address':owner}})
 a._retrieve_additional_info('request')
 assert calls==[('call',{'address':owner.lower(),'function':'foo'}),
                ('child','foo',owner.lower()),('source','foo',owner.lower())]


def test_empty_additional_info_is_an_explicit_no_op():
 a,calls=analyzer({})
 assert a._retrieve_additional_info('nothing else required')=={}
 assert calls==[]


def test_budget_stop_is_preserved_without_domain_error_callback():
 from faultseeker.core.spend_guard import BudgetApprovalRequired
 callbacks=[]
 a=FunctionAnalyzer(agent_factory=lambda *args:SimpleNamespace(),
                    analysis_error_handler=lambda error:callbacks.append(type(error).__name__))
 error=BudgetApprovalRequired('fixture budget boundary')
 with pytest.raises(BudgetApprovalRequired) as caught:a._record_analysis_error(error)
 assert caught.value is error
 assert callbacks==[] and a.analysis_errors==[]


def test_actual_function_loop_stops_after_schema_error_before_another_model_call(tmp_path,monkeypatch):
 from benchmark.nara_pilot_provider import NaraPilot,StudyStop,MODEL,ENDPOINT
 from faultseeker.core.llm_router import HybridLLMRouter,COST_RATES
 from faultseeker.core.spend_guard import SpendGuard
 rates={'input':.1,'output':.2}
 monkeypatch.setitem(COST_RATES,MODEL,rates)
 guard=SpendGuard(tmp_path/'simulation-ledger.json',pricing={MODEL:rates})
 router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',
                       remote_model_ids={MODEL},spend_guard=guard)
 contents=['Observed context from recorded input.','1. Inspect source.',
           json.dumps({'task_description':'Inspect the implementation','additional_information':'source'}),
           json.dumps({'source_code':['foo::moduleLookup']})]
 dispatched=[];now=[0.0]
 def cached_transport(url,headers,body,timeout):
  assert url==ENDPOINT
  dispatched.append(json.loads(body))
  assert len(dispatched)<=4, 'Domain failure must stop before another model dispatch'
  content=contents[len(dispatched)-1]
  response={'model':MODEL,'choices':[{'finish_reason':'stop','message':{'content':content}}],
            'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}
  return 200,json.dumps(response).encode(),ENDPOINT
 pilot=NaraPilot(api_key='offline-fixture-nonsecret',router=router,output_dir=tmp_path/'calls',
                 transport=cached_transport,clock=lambda:now[0],sleep=lambda n:now.__setitem__(0,now[0]+n))
 a=FunctionAnalyzer(model=MODEL,router=router,agent_factory=pilot.factory,
                    analysis_error_handler=pilot.stop_after_analysis_error)
 a.function_call_info_summary={'function':'foo','address':A,'high_appearance_count_children_calls':{}}
 lookups=[]
 a._retrieve_source_code=lambda *args:lookups.append(args) or []
 with pytest.raises(StudyStop):a._function_analysis_init()
 assert len(dispatched)==pilot.calls==4
 assert lookups==[]
 assert len(a.analysis_errors)==1
 assert a.analysis_errors[0]['error_type']=='AdditionalInfoSchemaError'
 assert a.analysis_errors[0]['function']=='foo' and a.analysis_errors[0]['address']==A
 assert pilot.stop_reason and 'moduleLookup' not in pilot.stop_reason
 events_before=list(guard.report()['events'])
 with pytest.raises(StudyStop):pilot.factory('system','processing_agent').query('must not dispatch')
 assert len(dispatched)==4 and guard.report()['events']==events_before
 assert [e['event'] for e in events_before]==['reserve','settle']*4
