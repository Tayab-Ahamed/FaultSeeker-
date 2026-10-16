"""Pure grouping of authenticated execution PCs and verified compiler inputs.

Caller validates captured trace/source bindings, runtime identity and metadata.
This helper never opens files, resolves names, or infers vulnerability/function
bodies. Groups use executing code address and the observed frame entry selector.
"""
from collections import Counter
from copy import deepcopy
import json
import re
from faultseeker.function_analysis.execution_source_map import map_execution_events,disassemble,SourceMapError

ADDRESS=re.compile(r'0x[0-9a-fA-F]{40}\Z')
SELECTOR=re.compile(r'0x(?:[0-9a-fA-F]{8})?\Z')
SCOPE='Observed storage opcode source spans for executing code and frame entry selector; not AST function slices or fault attribution'


def _frames(trace):
    frames={}
    def walk(node,inherited=None):
        if not isinstance(node,dict):raise SourceMapError('Canonical call frame required')
        code=node.get('callee');call_id=node.get('call_id');selector=node.get('function_selector')
        if not isinstance(code,str) or not ADDRESS.fullmatch(code):raise SourceMapError('Canonical code address required')
        if not isinstance(selector,str) or not SELECTOR.fullmatch(selector):raise SourceMapError('Canonical frame selector required')
        if call_id is None or call_id in frames:raise SourceMapError('Unique canonical call ID required')
        code=code.lower()
        storage=inherited if node.get('call_type') in ('DELEGATECALL','CALLCODE') else code
        if storage is None:raise SourceMapError('Delegated frame requires inherited storage owner')
        frames[call_id]={'code_address':code,'storage_address':storage,'selector':selector.lower()}
        for child in node.get('children',[]):walk(child,storage)
    if trace:walk(trace)
    return frames


def _compiler_runtime(response,evidence):
    runtime=response.get('runtimeBytecode') or {}
    onchain=runtime.get('onchainBytecode');compiled=runtime.get('recompiledBytecode')
    if not isinstance(onchain,str) or not isinstance(compiled,str):return None
    sources={};source_ids=response.get('sourceIds') or (response.get('stdJsonOutput') or {}).get('sources') or {}
    for path,record in source_ids.items():
        file_id=record.get('id');source=(response.get('sources') or {}).get(path)
        if type(file_id) is not int or file_id<0:raise SourceMapError('Compiler source ID must be nonnegative integer')
        if not source or not isinstance(source.get('content'),str):continue
        item={'path':path,'content':source['content'],'generated':False}
        if file_id in sources and sources[file_id]!=item:raise SourceMapError('Conflicting compiler source IDs')
        sources[file_id]=item
    outputs=(response.get('stdJsonOutput') or {}).get('contracts') or {}
    qualified=(response.get('compilation') or {}).get('fullyQualifiedName')
    selected=[]
    for path,names in outputs.items():
        for name,contract in names.items():
            deployed=(contract.get('evm') or {}).get('deployedBytecode') or {}
            if qualified:
                if path+':'+name==qualified:selected.append(deployed)
            elif str(deployed.get('object','')).removeprefix('0x').lower()==compiled.removeprefix('0x').lower():
                selected.append(deployed)
    for deployed in selected:
        for generated in deployed.get('generatedSources') or []:
            file_id=generated.get('id');content=generated.get('contents');name=generated.get('name')
            if type(file_id) is not int or file_id<0 or not isinstance(content,str) or not isinstance(name,str):
                raise SourceMapError('Invalid generated compiler source')
            item={'path':name,'content':content,'generated':True}
            if file_id in sources and sources[file_id]!=item:raise SourceMapError('Conflicting generated source ID')
            sources[file_id]=item
    source_map=runtime.get('sourceMap')
    unreliable=any(re.search(r'\bverbatim_\d+i_\d+o\s*\(',source['content']) for source in sources.values())
    return {'onchain_bytecode':onchain,'recompiled_bytecode':compiled,
        'source_map':source_map if isinstance(source_map,str) and not unreliable else '',
        'sources':sources,'immutable_references':runtime.get('immutableReferences'),
        'link_references':runtime.get('linkReferences'),'evidence':evidence,
        'source_map_unavailable':not isinstance(source_map,str) or not source_map,
        'source_map_unreliable':unreliable}


def build_execution_evidence(structured,contracts):
    """Return by_function[code_address][entry_selector] and explicit coverage.

    Exact repeated spans retain occurrence/event/call provenance. Generated or
    absent source is kept separate from mapped Solidity spans. No count is a
    quality score or a claim that a frame entry owns every executed source span.
    """
    frames=_frames(structured.get('trace'))
    runtimes={}
    for address,record in contracts.items():
        if not isinstance(address,str) or not ADDRESS.fullmatch(address) or address!=address.lower():
            raise SourceMapError('Compiler input key must be lowercase code address')
        runtime=_compiler_runtime(record['response'],record['evidence'])
        if runtime is not None:runtimes[address]=runtime
    by_function={};unavailable=[];totals=Counter();input_events=0;mapped_count=0
    for field,kind,expected_opcode in (('storage_reads','SLOAD','0x54'),('storage_events','SSTORE','0x55')):
        events=structured.get(field,[])
        for event,row in zip(events,map_execution_events(events,frames,runtimes)):
            input_events+=1;row['event_kind']=kind
            for field_name in ('slot','reverted'):
                if field_name in event:row[field_name]=deepcopy(event[field_name])
            if row.get('opcode') is not None and row['opcode']!=expected_opcode:
                raise SourceMapError('Recorded '+kind+' event differs from actual runtime opcode')
            frame=frames.get(event['call_id'])
            if frame is None:
                unavailable.append(row);totals[row['status']]+=1;continue
            code=frame['code_address'];selector=frame['selector']
            row['entry_selector']=selector
            if code in runtimes and runtimes[code]['source_map_unavailable']:
                row['status']='SOURCE_MAP_UNAVAILABLE'
            if code in runtimes and runtimes[code]['source_map_unreliable']:
                row['status']='UNRELIABLE_SOURCE_MAP_VERBATIM'
            group=by_function.setdefault(code,{}).setdefault(selector,
                {'mapped_spans':[],'non_solidity_spans':[],'unavailable_events':[],'unavailable_counts':{},'scope':SCOPE})
            status=row['status']
            if status=='MAPPED':mapped_count+=1;target=group['mapped_spans']
            else:
                unavailable.append(deepcopy(row));group['unavailable_events'].append(deepcopy(row))
                totals[status]+=1;group['unavailable_counts'][status]=group['unavailable_counts'].get(status,0)+1
                if status!='GENERATED_SOURCE':continue
                target=group['non_solidity_spans']
            # Compact exact PC/source/owner/provenance repetitions, preserving
            # every original event index and call-frame occurrence separately.
            identity={k:v for k,v in row.items() if k not in ('event_index','call_id')}
            key=json.dumps(identity,sort_keys=True)
            existing=next((item for item in target if item['_key']==key),None)
            occurrence={'event_index':event.get('event_index'),'call_id':event['call_id'],'pc':event['pc']}
            for field_name in ('slot','reverted'):
                if field_name in event:occurrence[field_name]=deepcopy(event[field_name])
            if existing is None:
                existing=deepcopy(identity);existing.update(_key=key,occurrence_count=0,event_indices=[],occurrences=[]);target.append(existing)
            existing['occurrence_count']+=1;existing['event_indices'].append(event.get('event_index'));existing['occurrences'].append(occurrence)
    for groups in by_function.values():
        for group in groups.values():
            for item in group['mapped_spans']+group['non_solidity_spans']:item.pop('_key',None)
    return {'by_function':by_function,'unavailable_events':unavailable,
        'summary':{'input_events':input_events,'mapped_occurrences':mapped_count,
            'unavailable_counts':dict(totals),'source_scope':SCOPE,'vulnerability_inferred':False}}
