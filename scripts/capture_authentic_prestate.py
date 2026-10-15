"""Recover actual pre-transaction code; prestate slots are not opcode events."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from dotenv import dotenv_values
from benchmark.research_protocol import admit, bind, read_bound, sha, write_json
from scripts.rebuild_authentic_cohort import BASE, drpc_url
from scripts.replay_historical_opcodes import MeteredRPC
from scripts.capture_authentic_traces import complexity_observation, walk


def enrich_capture(capture, prestate):
    if (not isinstance(prestate,dict) or not prestate
            or any(not isinstance(a,str) or not re.fullmatch('0x[0-9a-fA-F]{40}',a) for a in prestate)):
        raise ValueError('Non-diff prestate account map with full addresses required')
    result=deepcopy(capture)
    code=result['historical_code']
    evidence={}
    created={f.get('to','').lower() for f in walk(result['raw_trace']['call'])
             if f.get('type') in ('CREATE','CREATE2')}
    for address in list(code):
        account=prestate.get(address)
        if isinstance(account,dict) and address not in created:
            observed=account.get('code','0x')
            if not isinstance(observed,str) or not re.fullmatch('0x(?:[0-9a-fA-F]{2})*',observed):
                raise ValueError('Invalid prestate code bytes')
            code[address]=observed
            evidence[address]='prestateTracer non-diff mode, code capture enabled'
    result['code_evidence']=evidence
    try:
        result['complexity']=complexity_observation(result['raw_trace']['call'],code)
    except ValueError as error:
        result['complexity']={'complexity_class':'UNRECOVERED','reason':str(error)}
    result['prestate_scope']='Pre-transaction account code; storage is neither ordered opcode events nor proof of a storage hazard'
    return result


def archive(path,folder):
    if path.exists():
        raw=path.read_bytes()
        previous=folder/(sha(raw)+path.suffix)
        previous.parent.mkdir(parents=True,exist_ok=True)
        if previous.exists() and previous.read_bytes()!=raw:
            raise ValueError('Archive digest collision')
        if not previous.exists():
            previous.write_bytes(raw)


def run():
    endpoint=dotenv_values(ROOT/'.env').get('DRPC_RPC_URL')
    if not endpoint:
        raise ValueError('DRPC_RPC_URL required')
    records=[]
    for row in json.loads((BASE/'admitted_records.json').read_text()):
        if not admit(row,ROOT)['accepted']:
            raise ValueError('Invalidated admission')
        target=BASE/'prestate'/row['chain']/(row['txn_hash']+'.json.gz')
        result={'identity':row['chain']+':'+row['txn_hash']}
        if not target.exists():
            meter=MeteredRPC(drpc_url(endpoint,row['chain']),ROOT/'data/research/spend_ledger.json',max_requests=2)
            request={'jsonrpc':'2.0','id':1,'method':'debug_traceTransaction',
                'params':[row['txn_hash'],{'tracer':'prestateTracer','tracerConfig':{'diffMode':False,'disableCode':False,'disableStorage':False}}]}
            try:
                observed_chain=int(meter.rpc('eth_chainId',[]),16)
                if observed_chain!=json.loads(read_bound(row['rpc'],ROOT))['chain_id']:
                    raise ValueError('Wrong chain ID')
                response=meter.forward(request)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(gzip.compress(json.dumps({'transaction_hash':row['txn_hash'],'chain':row['chain'],
                    'rpc_identity':row['rpc'],'request':request,'response':response}).encode(),mtime=0))
            except Exception as error:
                result.update(status='UNAVAILABLE',error_type=type(error).__name__)
            result['accounting']=meter.summary()
        if target.exists():
            result['artifact']=bind(target,ROOT)
            response=json.loads(gzip.decompress(target.read_bytes()))['response']
            accounts=response.get('result')
            if isinstance(accounts,dict) and accounts and all(re.fullmatch('0x[0-9a-fA-F]{40}',a) for a in accounts):
                result.update(status='CAPTURED_PRESTATE',account_count=len(accounts))
                trace_path=BASE/'traces'/row['chain']/(row['txn_hash']+'.json.gz')
                if trace_path.exists():
                    capture=enrich_capture(json.loads(gzip.decompress(trace_path.read_bytes())),accounts)
                    capture['prestate_artifact']=result['artifact']
                    archive(trace_path,BASE/'trace_history')
                    trace_path.write_bytes(gzip.compress(json.dumps(capture).encode(),mtime=0))
                    result.update(trace_artifact=bind(trace_path,ROOT),complexity=capture['complexity'])
            else:
                result.update(status='UNAVAILABLE',rpc_error=response.get('error'))
        records.append(result)
        write_json(BASE/'prestate_acquisition.json',records)
        print(row['chain'],row['txn_hash'][:12],result.get('status'),flush=True)
    # Retain pre-enrichment request accounting before updating selected bindings.
    index=BASE/'trace_acquisition.json'
    archive(index,BASE/'trace_history')
    selected=json.loads(index.read_text()) if index.exists() else []
    for record in selected:
        match=next((r for r in records if r['identity']==record['identity'] and r.get('trace_artifact')),None)
        if match:
            record['artifact']=match['trace_artifact']
            record['complexity']=match['complexity']
    write_json(index,selected)


if __name__=='__main__':
    run()
