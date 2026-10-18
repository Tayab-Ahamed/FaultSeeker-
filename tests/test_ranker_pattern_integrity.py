"""Distinct repeated call evidence survives ranking without caller mutation."""
from copy import deepcopy
from types import SimpleNamespace
from faultseeker.function_analysis.function_ranker import FunctionRanker, rerank_saved_predictions
A='0x'+'11'*20
B='0x'+'22'*20

def call(fn,address=A):return {'function':fn,'address':address,'call_type':'call'}
def pattern(calls):return {'pattern':calls,'repeats':4}
def run(patterns):
 tx={'repeated_patterns':{'root':patterns},'function_call_loc_memo':{}}
 result=SimpleNamespace(address_calls_with_created_contract=[],functions_to_be_inspected={})
 return FunctionRanker().rank(result,tx)

def test_distinct_patterns_with_different_functions_or_contracts_survive():
 inputs=[pattern([call('foo')]),pattern([call('bar')]),pattern([call('foo',B)])]
 ranked=run(inputs)
 assert ranked.repeated_patterns==inputs

def test_exact_pattern_duplicate_is_deduplicated_but_call_order_is_preserved():
 ab=pattern([call('foo'),call('bar')]);ba=pattern([call('bar'),call('foo')])
 assert run([ab,deepcopy(ab),ba]).repeated_patterns==[ab,ba]

def test_ranking_does_not_share_mutable_pattern_evidence_with_caller():
 inputs=[pattern([call('foo'),call('bar')])];before=deepcopy(inputs)
 output=run(inputs)
 assert inputs==before
 output.repeated_patterns[0]['pattern'][0]['function']='changed'
 assert inputs==before

def test_different_occurrence_depths_and_repeat_counts_are_preserved():
 first=pattern([dict(call('foo'),depth=[0,1])])
 second=pattern([dict(call('foo'),depth=[0,2])])
 third=deepcopy(first);third['repeats']=5
 assert run([first,second,third]).repeated_patterns==[first,second,third]

def test_existing_filtered_none_and_single_staticcall_policy_is_unchanged():
 inputs=[pattern([call('balanceof')]),pattern([call(None)]),pattern([dict(call('foo'),call_type='staticcall')])]
 assert run(inputs).repeated_patterns==[]

def test_renderer_value_annotations_merge_into_one_function_candidate():
 ranked=rerank_saved_predictions([
  {'rank':1,'code_address':A,'function':'makeBid{value: 1}','count':1,
   'supporting_call_depths':[[0,1]]},
  {'rank':2,'code_address':A,'function':'makeBid{value: 2}','count':1,
   'supporting_call_depths':[[0,2,3]]},
 ])
 assert len(ranked)==1
 assert ranked[0]['function_name']=='makeBid'
 assert ranked[0]['count']==2
 assert ranked[0]['rank']==1

def test_depth_is_deterministic_tiebreak_after_count():
 ranked=rerank_saved_predictions([
  {'rank':1,'code_address':A,'function':'shallow','count':2,
   'supporting_call_depths':[[0,1]]},
  {'rank':2,'code_address':B,'function':'deep','count':2,
   'supporting_call_depths':[[0,1,2,3]]},
  ])
 assert [item['function_name'] for item in ranked]==['deep','shallow']

def test_path_concentration_precedes_raw_count_for_broad_fanout():
  ranked=rerank_saved_predictions([
   {'rank':1,'code_address':A,'function':'broad','count':5,
    'supporting_call_depths':[[0,1],[1,1],[2,1]]},
   {'rank':2,'code_address':B,'function':'concentrated','count':4,
    'supporting_call_depths':[[0,1,2],[0,1,3],[0,1,4],[0,1,5]]},
  ])
  assert [item['function_name'] for item in ranked]==['concentrated','broad']
  assert ranked[0]['path_concentration']==4.0
  assert ranked[1]['path_concentration']==5/3
