"""Execution/source map primitives; deterministic, no network or state access."""
import pytest
from faultseeker.function_analysis.execution_source_map import (
    disassemble,validate_runtime_layout,decode_source_map,source_span,map_execution_events,SourceMapError)


def test_disassembly_skips_push_operands_and_handles_push0_and_truncation():
    instructions=disassemble('0x60fe7f'+'11'*32+'5f55')
    assert [(i.pc,i.opcode) for i in instructions]==[(0,0x60),(2,0x7f),(35,0x5f),(36,0x55)]
    assert [(i.pc,i.opcode) for i in disassemble('0x61aa')]==[(0,0x61)]


def test_compressed_source_map_inherits_fields_and_marks_unmapped_and_generated():
    rows=decode_source_map('0:4:0:i:0;:2::o;8:3:1;;-1:-1:-1')
    assert rows[1]=={'start':0,'length':2,'file_id':0,'jump':'o','modifier_depth':0}
    assert rows[3]==rows[2]
    assert rows[4]['file_id']==-1
    assert source_span(rows[4],{})['status']=='UNMAPPED'
    assert source_span(rows[2],{1:{'path':'generated.yul','content':'01234567890123','generated':True}})['status']=='GENERATED_SOURCE'


def test_utf8_offsets_are_byte_offsets_with_correct_lines_and_columns():
    text='α\n  βx\nend'
    result=source_span({'start':5,'length':3,'file_id':0}, {0:{'path':'x.sol','content':text}})
    assert result['excerpt']=='βx'
    assert (result['start_line'],result['start_column'],result['end_line'])==(2,3,2)
    with pytest.raises(SourceMapError):source_span({'start':6,'length':1,'file_id':0},{0:{'path':'x.sol','content':text}})


def test_runtime_patch_only_allows_equal_layout_push_operands():
    assert validate_runtime_layout('0x73'+'11'*20+'55','0x73'+'00'*20+'55',
        link_references={'x.sol':{'Lib':[{'start':1,'length':20}]}})['verified'] is True
    with pytest.raises(SourceMapError):validate_runtime_layout('0x601155','0x600055')
    with pytest.raises(SourceMapError):validate_runtime_layout('0x611155','0x601155',immutable_references={'1':[{'start':0,'length':1}]})
    with pytest.raises(SourceMapError):validate_runtime_layout('0x601155','0x600055',immutable_references={'1':[{'start':1,'length':2}]})
    assert validate_runtime_layout('0x601155','0x600055',immutable_references={'1':[{'start':1,'length':1}]})['patched_bytes']==1


def test_mapping_resolves_code_owner_separately_from_storage_owner():
    code='0x'+'11'*20; storage='0x'+'22'*20
    events=[{'call_id':3,'pc':2,'address':storage,'slot':'0x0','event_index':8}]
    runtime={code:{'onchain_bytecode':'0x600155','recompiled_bytecode':'0x600155',
        'source_map':'0:1:0;2:5:0','sources':{0:{'path':'x.sol','content':'x SSTORE'}}}}
    result=map_execution_events(events,{3:{'code_address':code,'storage_address':storage}},runtime)
    assert result[0]['code_address']==code and result[0]['storage_address']==storage
    assert result[0]['source']['excerpt']=='SSTOR'
    assert result[0]['opcode']=='0x55'


@pytest.mark.parametrize('mapping', ['', '0:1:0'])
def test_missing_instruction_source_is_explicit(mapping):
    address='0x'+'11'*20
    result=map_execution_events([{'call_id':0,'pc':2,'address':address}],
        {0:{'code_address':address,'storage_address':address}},
        {address:{'onchain_bytecode':'0x600155','recompiled_bytecode':'0x600155','source_map':mapping,'sources':{0:{'path':'x','content':'x'}}}})
    assert result[0]['status']=='UNMAPPED'


def test_event_program_counter_cannot_point_inside_push_data():
    address='0x'+'11'*20
    with pytest.raises(SourceMapError):map_execution_events([{'call_id':0,'pc':1,'address':address}],
        {0:{'code_address':address,'storage_address':address}},
        {address:{'onchain_bytecode':'0x600155','recompiled_bytecode':'0x600155','source_map':'0:1:0;0:1:0','sources':{}}})

@pytest.mark.parametrize('tx',[
 '0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d',
 '0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'])
def test_genuine_hash_bound_train_storage_pcs_map_to_verified_source_inputs(tx):
    import gzip,json
    from pathlib import Path
    from benchmark.research_protocol import read_bound
    from faultseeker.utils.rpc_provider import normalize_trace_node
    root=Path(__file__).resolve().parents[1]
    protocol=json.loads((root/'reports/cohort_rebuild_v2/localization_train_protocol.json').read_text())
    evidence=json.loads(read_bound(protocol['targets'],root))
    case=next(c for c in evidence['cases'] if c['identity']=='eth:'+tx)
    prestate=json.loads(gzip.decompress(read_bound(case['prestate'],root)))['response']['result']
    runtimes={}
    for contract in case['contracts']:
        if not contract.get('response'):continue
        data=json.loads(read_bound(contract['response'],root));address=contract['address'].lower()
        runtime=data['runtimeBytecode']
        assert runtime['onchainBytecode'].lower()==prestate[address]['code'].lower()
        sources={item['id']:{'path':path,'content':data['sources'][path]['content']} for path,item in data['sourceIds'].items()}
        runtimes[address]={'onchain_bytecode':runtime['onchainBytecode'],
            'recompiled_bytecode':runtime['recompiledBytecode'],'immutable_references':runtime.get('immutableReferences'),
            'link_references':runtime.get('linkReferences'),'source_map':runtime['sourceMap'],'sources':sources,
            'evidence':contract['response']}
    acquisition=json.loads((root/'reports/cohort_rebuild_v2/opcode_acquisition_train.json').read_text())
    binding=next(a['artifact'] for a in acquisition['attempts'] if a['identity']=='eth:'+tx and a.get('artifact'))
    capture=json.loads(gzip.decompress(read_bound(binding,root)))
    canonical=normalize_trace_node(capture['raw_trace']['call']);frames={}
    def walk(node,inherited=None):
        code=node['callee'].lower()
        storage=inherited if node['call_type'] in ('DELEGATECALL','CALLCODE') else code
        frames[node['call_id']]={'code_address':code,'storage_address':storage}
        for child in node['children']:walk(child,storage)
    walk(canonical)
    events=[event for event in capture['normalization']['storage_events'] if frames[event['call_id']]['code_address'] in runtimes]
    assert events
    mapped=map_execution_events(events,frames,runtimes)
    assert all(row['opcode']=='0x55' for row in mapped)
    actual=[row for row in mapped if row['status']=='MAPPED']
    assert actual and all(row['source']['byte_length']>=0 for row in actual)
    assert all(len(row['source']['excerpt'])<=240 for row in actual)
    assert all(row['evidence']==runtimes[row['code_address']]['evidence'] for row in mapped)
    if tx.startswith('0xc310'):
        assert any(row['code_address']!=row['storage_address'] for row in actual)


@pytest.mark.parametrize('encoded',['0:1:0:x','0:1:-2','-2:1:0','0:1:0:-:x','0:1:0:-:-1','0:1:0:-:0:extra'])
def test_malformed_source_maps_reject(encoded):
    with pytest.raises(SourceMapError):decode_source_map(encoded)


def test_unavailable_file_and_large_excerpt_stay_explicit():
    assert source_span({'file_id':12,'start':0,'length':1},{})['status']=='SOURCE_UNAVAILABLE'
    mapped=source_span({'file_id':0,'start':0,'length':1000},{0:{'path':'x.sol','content':'x'*1000}})
    assert len(mapped['excerpt'])==240 and mapped['excerpt_truncated'] is True
