import importlib.util
from pathlib import Path
import sys
sys.modules['readline']=None
import pytest
from faultseeker.function_analysis.prompt_call_identity import observed_call_references
A='0x'+'11'*20
B='0x'+'22'*20
S='0x12345678'

def test_incoming_functions_and_actual_direct_delegate_children():
 child={'address':B,'function':'0xaabbccdd','call_type':'delegatecall','children':[]}
 root={'address':A,'function':S,'call_type':'call','children':[child]}
 result=observed_call_references(A.upper().replace('0X','0x'),S,{A:[S,'other']},root)
 assert result=={'observed_entry_functions_at_address':[{'address':A,'function':S},{'address':A,'function':'other'}], 'observed_child_calls':[{'address':B,'function':'0xaabbccdd','call_type':'delegatecall','depth':[0,0],'parent_depth':[0]}]}
 assert 'depth' not in child

def test_only_requested_parent_and_direct_children_per_occurrence():
 child={'address':B,'function':'child','call_type':'CALL','depth':[0,5,2],'children':[]}
 roots=[{'address':A,'function':S,'children':[child],'depth':[0,5]}, {'address':A,'function':'other','children':[child]}, {'address':A,'function':S,'children':[child],'depth':[2]}]
 result=observed_call_references(A,S,{A:[S]},roots)
 assert [x['parent_depth'] for x in result['observed_child_calls']]==[[0,5],[2]]
 assert all(x['depth']==[0,5,2] for x in result['observed_child_calls'])

def test_explicit_empty_fields():
 assert observed_call_references(A,S,{},[])=={'observed_entry_functions_at_address':[],'observed_child_calls':[]}

@pytest.mark.parametrize('target',[{'address':'0xaabbccdd','function':'child'},{'address':B,'function':42}])
def test_invalid_child_reference_rejected(target):
 with pytest.raises(ValueError):observed_call_references(A,S,{A:[S]},{'address':A,'function':S,'children':[target]})

def test_real_train_euler_proxy_direct_child():
 from benchmark.captured_inputs import load_train_inputs
 from faultseeker.data_collection.txn_sequencer import TransactionSequencer
 root=Path(__file__).resolve().parents[1]
 inputs=load_train_inputs(root,'eth:0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d',require_opcodes=False)
 legacy=TransactionSequencer._canonical_to_legacy_trace(inputs.structured['trace'])
 incoming={}
 def walk(node):
  if node.get('function'):incoming.setdefault(node['address'].lower(),[]).append(node['function'])
  for child in node.get('children',[]):walk(child)
 walk(legacy)
 result=observed_call_references('0xe025e3ca2be02316033184551d4d3aa22024d9dc','0xe2bbb158',incoming,legacy)
 assert any(x['address']=='0x27182842e098f60e3d576794a5bffb0777e025d3' and x['function']=='0xe9c4a3ac' and x['call_type']=='call' for x in result['observed_child_calls'])
 assert all(len(x['address'])==42 for x in result['observed_child_calls'])
 assert observed_call_references('0xe025e3ca2be02316033184551d4d3aa22024d9dc','0x03ddf252',incoming,legacy)['observed_child_calls']==[]

def test_real_saved_bad_model_response_is_still_rejected():
 import json
 from faultseeker.function_analysis.additional_info_schema import normalize_additional_info
 root=Path(__file__).resolve().parents[1]
 record=json.loads((root/'reports/cohort_rebuild_v2/gateway_runs/20261016T050541-198e808b/calls/call-007.json').read_text(encoding='utf-8'))
 value=json.loads(record['response']['choices'][0]['message']['content'])
 with pytest.raises(ValueError):normalize_additional_info(value)
