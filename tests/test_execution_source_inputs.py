"""Pure execution evidence grouping; runtime and source provenance stays explicit."""
import pytest
from benchmark.execution_source_inputs import build_execution_evidence
from faultseeker.function_analysis.execution_source_map import SourceMapError
A='0x'+'11'*20
B='0x'+'22'*20
S='0x12345678'


def fixture():
 trace={'call_id':'0','callee':B,'call_type':'CALL','function_selector':'0xabcdefab','children':[
  {'call_id':'0.0','callee':A,'call_type':'DELEGATECALL','function_selector':S,'children':[]}]}
 structured={'trace':trace,'storage_reads':[],'storage_events':[
  {'call_id':'0.0','address':B,'pc':2,'event_index':4},
  {'call_id':'0.0','address':B,'pc':2,'event_index':9}]}
 response={'runtimeBytecode':{'onchainBytecode':'0x600155','recompiledBytecode':'0x600155','sourceMap':'0:1:0;2:6:0'},
  'sourceIds':{'x.sol':{'id':0}},'sources':{'x.sol':{'content':'x SSTORE'}},'stdJsonOutput':{}}
 return structured,{A:{'response':response,'evidence':{'path':'cached.json','sha256':'a'*64}}}


def test_groups_only_actual_code_owner_and_frame_selector_compacting_occurrences():
 structured,contracts=fixture();report=build_execution_evidence(structured,contracts)
 group=report['by_function'][A][S]
 assert len(group['mapped_spans'])==1
 span=group['mapped_spans'][0]
 assert span['occurrence_count']==2 and span['event_indices']==[4,9]
 assert span['code_address']==A and span['storage_address']==B
 assert span['event_kind']=='SSTORE' and span['opcode']=='0x55'
 assert span['source']['excerpt']=='SSTORE'
 assert span['evidence']==contracts[A]['evidence']
 assert report['summary']['input_events']==2
 assert report['summary']['mapped_occurrences']==2


def test_storage_read_must_match_actual_sload_opcode():
 structured,contracts=fixture();structured['storage_reads']=structured.pop('storage_events')
 with pytest.raises(SourceMapError,match='opcode'):build_execution_evidence(structured,contracts)


def test_uncached_runtime_and_unknown_frame_are_not_fabricated():
 structured,_=fixture();structured['storage_events'].append({'call_id':'unknown','address':B,'pc':2,'event_index':10})
 result=build_execution_evidence(structured,{})
 assert result['by_function'][A][S]['unavailable_counts']=={'RUNTIME_UNAVAILABLE':2}
 assert result['summary']['unavailable_counts']=={'RUNTIME_UNAVAILABLE':2,'FRAME_UNAVAILABLE':1}
 assert any(row['status']=='FRAME_UNAVAILABLE' for row in result['unavailable_events'])


def test_generated_sources_are_retained_as_generated_not_solidity_function():
 structured,contracts=fixture();response=contracts[A]['response']
 response['runtimeBytecode']['sourceMap']='0:1:0;0:6:1'
 response['stdJsonOutput']={'contracts':{'x.sol':{'C':{'evm':{'deployedBytecode':{
  'object':'600155','generatedSources':[{'id':1,'name':'generated.yul','contents':'sstore'}]}}}}}}
 result=build_execution_evidence(structured,contracts)
 group=result['by_function'][A][S]
 assert group['mapped_spans']==[]
 assert group['unavailable_counts']=={'GENERATED_SOURCE':2}
 assert group['non_solidity_spans'][0]['source']['path']=='generated.yul'


def test_root_call_and_delegatecall_retain_different_entry_selectors():
 structured,contracts=fixture();structured['trace']['children'][0]['call_type']='CALLCODE'
 result=build_execution_evidence(structured,contracts)
 assert set(result['by_function'][A])=={S}
 assert B not in result['by_function']


def test_missing_compiler_source_inputs_stays_unavailable():
 structured,contracts=fixture();contracts[A]['response']['runtimeBytecode']['sourceMap']=None
 result=build_execution_evidence(structured,contracts)
 assert result['by_function'][A][S]['unavailable_counts']=={'SOURCE_MAP_UNAVAILABLE':2}


def test_yul_verbatim_builtin_makes_instruction_map_explicitly_unreliable():
 structured,contracts=fixture();contracts[A]['response']['sources']['x.sol']['content']='verbatim_1i_1o(hex"00", x)'
 result=build_execution_evidence(structured,contracts)
 group=result['by_function'][A][S]
 assert group['mapped_spans']==[]
 assert group['unavailable_counts']=={'UNRELIABLE_SOURCE_MAP_VERBATIM':2}


def test_known_unavailable_source_retains_exact_event_owner_and_provenance():
 structured,contracts=fixture();contracts[A]['response']['sources']={}
 result=build_execution_evidence(structured,contracts)
 group=result['by_function'][A][S]
 assert group['unavailable_counts']=={'SOURCE_UNAVAILABLE':2}
 assert group['unavailable_events'][0]['code_address']==A
 assert group['unavailable_events'][0]['storage_address']==B
 assert group['unavailable_events'][0]['event_index']==4
 assert group['unavailable_events'][0]['evidence']==contracts[A]['evidence']

@pytest.mark.parametrize('tx',[
 '0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d',
 '0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'])
def test_genuine_verified_train_inputs_group_actual_storage_source_evidence(tx):
 import json
 from pathlib import Path
 from benchmark.research_protocol import read_bound
 from benchmark.captured_inputs import load_train_inputs
 from benchmark.verified_source_inputs import VerifiedSourceDownloader
 root=Path(__file__).resolve().parents[1]
 protocol=json.loads((root/'reports/cohort_rebuild_v2/localization_train_protocol.json').read_text())
 evidence_binding=protocol['targets'];evidence=json.loads(read_bound(evidence_binding,root))
 case=next(c for c in evidence['cases'] if c['identity']=='eth:'+tx)
 contracts={c['address'].lower():{'response':json.loads(read_bound(c['response'],root)),'evidence':c['response']}
            for c in case['contracts'] if c.get('response')}
 verifier=VerifiedSourceDownloader.factory(root=root,evidence_binding=evidence_binding,train_identity='eth:'+tx)
 verifier('eth',list(contracts)).run()
 inputs=load_train_inputs(root,'eth:'+tx)
 report=build_execution_evidence(inputs.structured,contracts)
 assert report['summary']['mapped_occurrences']>0
 assert report['summary']['input_events']==len(inputs.structured['storage_reads'])+len(inputs.structured['storage_events'])
 assert report['summary']['vulnerability_inferred'] is False
 for address,groups in report['by_function'].items():
  for selector,group in groups.items():
   assert selector=='0x' or len(selector)==10
   for span in group['mapped_spans']:
    assert span['code_address']==address and span['entry_selector']==selector
    assert span['evidence']==contracts[address]['evidence']
    assert span['opcode']==('0x54' if span['event_kind']=='SLOAD' else '0x55')
    assert span['source']['source_utf8_sha256']
    assert len(span['event_indices'])==span['occurrence_count']


def test_slot_and_reverted_write_provenance_survive_grouping():
 structured,contracts=fixture()
 structured['storage_events'][0].update(slot='0x1',reverted=True)
 structured['storage_events'][1].update(slot='0x2',reverted=False)
 result=build_execution_evidence(structured,contracts)
 spans=result['by_function'][A][S]['mapped_spans']
 assert len(spans)==2
 assert [(s['slot'],s['reverted']) for s in spans]==[('0x1',True),('0x2',False)]
 assert [(s['occurrences'][0]['slot'],s['occurrences'][0]['reverted']) for s in spans]==[('0x1',True),('0x2',False)]
