"""Pure execution-backed Solidity source locations, never fault attribution.

Callers must verify historical runtime/source provenance before supplying input.
PCs refer to the executing code address, distinct from the storage owner under
DELEGATECALL/CALLCODE. Missing code/source/generated locations stay explicit.
"""
from dataclasses import dataclass
import hashlib
import re

ADDRESS=re.compile(r'0x[0-9a-fA-F]{40}\Z')

class SourceMapError(ValueError):
    pass

@dataclass(frozen=True)
class Instruction:
    pc: int
    opcode: int
    immediate_start: int
    immediate_end: int


def _bytes(value):
    if isinstance(value,bytes):return value
    if not isinstance(value,str) or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*',value):
        raise SourceMapError('Bytecode must be exact hexadecimal bytes')
    return bytes.fromhex(value[2:])


def disassemble(bytecode):
    """Instruction boundaries skip PUSH1..32 operands; PUSH0 has no operand.

    Truncated final PUSH instructions are retained with the available operand;
    EVM implicit zero padding is not invented in the recorded byte sequence.
    """
    raw=_bytes(bytecode);pc=0;result=[]
    while pc<len(raw):
        opcode=raw[pc];width=opcode-0x5f if 0x60<=opcode<=0x7f else 0
        result.append(Instruction(pc,opcode,pc+1,min(len(raw),pc+1+width)))
        pc+=1+width
    return tuple(result)


def _ranges(value):
    if value is None:return []
    if isinstance(value,dict):
        if 'start' in value or 'length' in value:
            if set(value)!={'start','length'} or any(type(value[k]) is not int for k in ('start','length')):
                raise SourceMapError('Invalid compiler patch range')
            if value['start']<0 or value['length']<=0:raise SourceMapError('Invalid compiler patch bounds')
            return [(value['start'],value['start']+value['length'])]
        return [item for child in value.values() for item in _ranges(child)]
    if isinstance(value,list):return [item for child in value for item in _ranges(child)]
    raise SourceMapError('Invalid compiler patch reference container')


def validate_runtime_layout(onchain,recompiled,*,immutable_references=None,link_references=None):
    """Permit byte differences only inside explicitly declared PUSH operands.

    References authorize operand replacement, never instruction insertion,
    opcode replacement, altered PUSH width, auxiliary metadata, or unknown diffs.
    """
    actual,compiled=_bytes(onchain),_bytes(recompiled)
    if len(actual)!=len(compiled):raise SourceMapError('Runtime lengths differ')
    instructions=disassemble(actual);other=disassemble(compiled)
    if [(i.pc,i.opcode) for i in instructions]!=[(i.pc,i.opcode) for i in other]:
        raise SourceMapError('Runtime opcode layout differs')
    ranges=_ranges(immutable_references)+_ranges(link_references)
    allowed=set()
    for start,end in ranges:
        if end>len(actual) or not any(i.immediate_start<=start<end<=i.immediate_end and 0x60<=i.opcode<=0x7f for i in instructions):
            raise SourceMapError('Compiler patch must lie within one PUSH immediate')
        allowed.update(range(start,end))
    differences={i for i,(a,b) in enumerate(zip(actual,compiled)) if a!=b}
    if not differences<=allowed:raise SourceMapError('Runtime differs outside validated compiler patches')
    return {'verified':True,'patched_bytes':len(differences),'instruction_count':len(instructions),
            'onchain_runtime_sha256':hashlib.sha256(actual).hexdigest(),
            'recompiled_runtime_sha256':hashlib.sha256(compiled).hexdigest()}


def decode_source_map(value):
    """Expand start:length:file:jump:modifier compressed Solidity entries."""
    if not isinstance(value,str):raise SourceMapError('Source map must be a string')
    if value=='':return []
    previous={'start':0,'length':0,'file_id':-1,'jump':'-','modifier_depth':0};rows=[]
    names=('start','length','file_id','jump','modifier_depth')
    for entry in value.split(';'):
        fields=entry.split(':')
        if len(fields)>5:raise SourceMapError('Too many source map fields')
        row=dict(previous)
        for name,text in zip(names,fields):
            if not text:continue
            if name=='jump':
                if text not in ('i','o','-'):raise SourceMapError('Invalid source map jump')
                row[name]=text
            else:
                if not re.fullmatch(r'-?\d+',text):raise SourceMapError('Invalid source map integer')
                row[name]=int(text)
        if (row['file_id'] < -1 or row['modifier_depth']<0
            or row['start'] < -1 or row['length'] < -1
            or row['file_id']>=0 and (row['start']<0 or row['length']<0)):
            raise SourceMapError('Invalid source map location')
        rows.append(row);previous=row
    return rows


def source_span(location,sources):
    """Byte-accurate range with one-based Unicode columns, exclusive end.

    Excerpts are capped to 240 characters. Locations retain complete byte bounds;
    generated source is explicitly labelled rather than called Solidity source.
    """
    file_id=location['file_id']
    if file_id==-1:return {'status':'UNMAPPED','file_id':-1}
    source=sources.get(file_id)
    if source is None:return {'status':'SOURCE_UNAVAILABLE','file_id':file_id}
    if not isinstance(source,dict) or not isinstance(source.get('content'),str) or not isinstance(source.get('path'),str):
        raise SourceMapError('Source content/path unavailable')
    raw=source['content'].encode('utf-8');start,length=location['start'],location['length']
    if type(start) is not int or type(length) is not int or start<0 or length<0 or start+length>len(raw):
        raise SourceMapError('Source byte range exceeds supplied file')
    try:
        prefix=raw[:start].decode('utf-8');text=raw[start:start+length].decode('utf-8');end_prefix=raw[:start+length].decode('utf-8')
    except UnicodeDecodeError:raise SourceMapError('Source range splits a UTF-8 character') from None
    return {'status':'GENERATED_SOURCE' if source.get('generated') is True else 'MAPPED',
        'file_id':file_id,'path':source['path'],'byte_start':start,'byte_length':length,
        'start_line':prefix.count('\n')+1,'start_column':len(prefix.rsplit('\n',1)[-1])+1,
        'end_line':end_prefix.count('\n')+1,'end_column':len(end_prefix.rsplit('\n',1)[-1])+1,
        'source_utf8_sha256':hashlib.sha256(raw).hexdigest(),'excerpt':text[:240],'excerpt_truncated':len(text)>240}


def _address(value):
    if not isinstance(value,str) or not ADDRESS.fullmatch(value):raise SourceMapError('Full code/storage address required')
    return value.lower()


def map_execution_events(events,frames,runtimes):
    """Join authentic event PCs to caller-supplied verified runtime/source inputs.

    frames maps call_id to code_address/storage_address. Runtime fields are
    onchain_bytecode, recompiled_bytecode, source_map, sources (integer file IDs),
    plus optional immutable_references/link_references and evidence bindings.
    No entry function identity or vulnerability is inferred from a source span.
    """
    cache={};result=[]
    for event in events:
        row={'call_id':event['call_id'],'pc':event['pc'],'event_index':event.get('event_index')}
        frame=frames.get(event['call_id'])
        if frame is None:
            result.append(dict(row,status='FRAME_UNAVAILABLE'));continue
        code,storage=_address(frame['code_address']),_address(frame['storage_address'])
        if _address(event['address'])!=storage:raise SourceMapError('Event storage owner differs from bound frame')
        row.update(code_address=code,storage_address=storage)
        if code not in runtimes:
            result.append(dict(row,status='RUNTIME_UNAVAILABLE'));continue
        if code not in cache:
            runtime=runtimes[code]
            proof=validate_runtime_layout(runtime['onchain_bytecode'],runtime['recompiled_bytecode'],
                immutable_references=runtime.get('immutable_references'),link_references=runtime.get('link_references'))
            instructions=disassemble(runtime['onchain_bytecode'])
            cache[code]=(runtime,proof,{i.pc:(index,i) for index,i in enumerate(instructions)},decode_source_map(runtime['source_map']))
        runtime,proof,by_pc,locations=cache[code]
        pc=event['pc']
        if type(pc) is not int or pc not in by_pc:raise SourceMapError('Event PC is not an instruction boundary')
        index,instruction=by_pc[pc];row.update(opcode='0x'+format(instruction.opcode,'02x'),runtime_proof=proof)
        if index>=len(locations):
            row['status']='UNMAPPED'
        else:
            row['source']=source_span(locations[index],runtime['sources']);row['status']=row['source']['status']
        if runtime.get('evidence') is not None:row['evidence']=runtime['evidence']
        result.append(row)
    return result
