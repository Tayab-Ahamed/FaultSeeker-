"""Capture actual call traces and historical contract code for admitted identities.

No opcode or storage observation is synthesized from call traces. Complexity is
the count of unique (contract address, input selector) pairs, including a single
empty selector for a contract's fallback/receive path. EOAs are excluded using
historical eth_getCode, not an address-name heuristic.
"""
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from dotenv import dotenv_values
from benchmark.research_protocol import bind, read_bound, write_json, admit
from scripts.rebuild_authentic_cohort import BASE, drpc_url
from scripts.replay_historical_opcodes import MeteredRPC


def walk(node):
    yield node
    for child in node.get('calls',[]):
        yield from walk(child)


def validate_call_identity(trace, transaction, receipt=None):
    if not isinstance(trace,dict) or trace.get('error'):
        raise ValueError('Successful call trace required')
    expected=dict(transaction)
    if transaction.get('to') is None:
        if trace.get('type') not in ('CREATE','CREATE2') or not (receipt or {}).get('contractAddress'):
            raise ValueError('Contract creation identity requires its canonical receipt')
        expected['to']=receipt['contractAddress']
    for field in ('from','to'):
        if str(trace.get(field,'')).lower()!=str(expected.get(field,'')).lower():
            raise ValueError('Call trace transaction identity mismatch')


def complexity_observation(trace, code):
    frames=list(walk(trace))
    unique=set()
    for frame in frames:
        address=frame.get('to','').lower()
        if not address:
            raise ValueError('Call target code cannot be verified')
        if address not in code or not isinstance(code[address],str) or not code[address].startswith('0x'):
            raise ValueError('Historical contract code missing')
        if code[address]=='0x' and frame.get('calls'):
            raise ValueError('Historical code missing for an executed contract, possibly destroyed')
        if code[address]!='0x':
            unique.add((address,frame.get('input','0x')[:10].lower()))
    count=len(unique)
    return {'unique_function_calls':count,'trace_frames':len(frames),
        'complexity_class':'Simple' if count<=5 else 'Moderate' if count<=50 else 'Complex' if count<=500 else 'Exceptionally Complex',
        'definition':'Unique contract address and input selector pairs, verified with post-block code; empty input denotes fallback/receive. EOAs excluded. Self-destructed targets may need pre-state code.',
        'unique_functions':[{'address':a,'selector':s} for a,s in sorted(unique)]}


def run():
    endpoint=dotenv_values(ROOT/'.env').get('DRPC_RPC_URL')
    if not endpoint:
        raise ValueError('DRPC_RPC_URL required')
    results=[]
    for row in json.loads((BASE/'admitted_records.json').read_text()):
        if not admit(row,ROOT)['accepted']:
            raise ValueError('Admission no longer valid')
        target=BASE/'traces'/row['chain']/(row['txn_hash']+'.json.gz')
        if target.exists():
            results.append({'identity':row['chain']+':'+row['txn_hash'],'artifact':bind(target,ROOT),'status':'RECORDED'})
            continue
        meter=MeteredRPC(drpc_url(endpoint,row['chain']),ROOT/'data/research/spend_ledger.json',max_requests=1000)
        result={'identity':row['chain']+':'+row['txn_hash'],'status':'UNAVAILABLE'}
        rpc=json.loads(read_bound(row['rpc'],ROOT))
        try:
            observed_chain=int(meter.rpc('eth_chainId',[]),16)
            if observed_chain!=rpc['chain_id']:
                raise ValueError('Wrong RPC chain')
            response=meter.forward({'jsonrpc':'2.0','id':1,'method':'debug_traceTransaction',
                                   'params':[row['txn_hash'],{'tracer':'callTracer'}]})
            if response.get('error') or not isinstance(response.get('result'),dict):
                result.update(rpc_error=response.get('error'),reason='callTracer returned no trace')
            else:
                trace=response['result']
                validate_call_identity(trace,rpc['transaction'],rpc['receipt'])
                addresses=sorted({f.get('to','').lower() for f in walk(trace)}- {''})
                code={}
                def get_code(address):
                    try:
                        return address,meter.rpc('eth_getCode',[address,rpc['receipt']['blockNumber']])
                    except Exception:
                        return address,None
                with ThreadPoolExecutor(max_workers=4) as pool:
                    code.update(pool.map(get_code,addresses))
                capture={'transaction_hash':row['txn_hash'],'chain':row['chain'],
                    'raw_trace':{'call':trace},'storage_trace_complete':False,
                    'rpc_identity':row['rpc'],'historical_code':code,
                    'capture_version':'live-callTracer-with-historical-code-v1'}
                try:
                    capture['complexity']=complexity_observation(trace,code)
                except ValueError as error:
                    capture['complexity']={'complexity_class':'UNRECOVERED','reason':str(error)}
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(gzip.compress(json.dumps(capture).encode(),mtime=0))
                result.update(status='CAPTURED_CALL_TRACE',artifact=bind(target,ROOT),complexity=capture['complexity'])
        except Exception as error:
            result['error_type']=type(error).__name__
        result['accounting']=meter.summary()
        results.append(result)
        write_json(BASE/'trace_acquisition.json',results)
        print(row['chain'],row['txn_hash'][:12],result['status'],flush=True)
    write_json(BASE/'trace_acquisition.json',results)


if __name__=='__main__':
    run()
