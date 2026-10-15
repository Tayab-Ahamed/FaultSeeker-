"""Offline, train-only integration of hash-bound real provider traces."""
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from benchmark.research_protocol import load_train, read_bound, bind, sha, write_json
from scripts.probe_train_chain_traces import parity_call_tree, validate_trace
from scripts.capture_authentic_traces import walk

def integrate(root=ROOT,write_index=True):
    root=Path(root)
    base=root/'reports/cohort_rebuild_v2'
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    rows={r['chain']+':'+r['txn_hash']:r for r in load_train(split,root)}
    report=json.loads((base/'chain_trace_probe/network_continuation/probe.json').read_text(encoding='utf-8'))
    accepted=[]
    for observation in report['observations']:
        for attempt in observation['attempts']:
            if attempt.get('status')!='CAPTURED': continue
            row=rows[observation['identity']]
            raw=json.loads(gzip.decompress(read_bound(attempt['artifact'],root)))
            if raw['transaction_hash']!=row['txn_hash'] or raw['chain']!=row['chain'] or raw['rpc_identity']!=row['rpc']:
                raise ValueError('Probe capture binding differs from frozen train')
            rpc=json.loads(read_bound(row['rpc'],root))
            tree=parity_call_tree(raw['result'],rpc['transaction'],rpc['receipt']) if raw['method']=='trace_transaction' else raw['result']
            validate_trace(tree,rpc['transaction'],rpc['receipt'])
            capture={'transaction_hash':row['txn_hash'],'chain':row['chain'],'raw_trace':{'call':tree},
                'rpc_identity':row['rpc'],'provider_capture':attempt['artifact'],
                'storage_trace_complete':False,'historical_code':{},
                'capture_version':'verified-provider-call-tree-v1',
                'complexity':{'complexity_class':'UNRECOVERED','reason':'Historical contract code not acquired; no inferred complexity'}}
            path=base/'chain_trace_probe/integrated'/(row['chain']+'-'+row['txn_hash']+'.json.gz')
            payload=gzip.compress(json.dumps(capture,sort_keys=True).encode(),mtime=0)
            if path.exists() and path.read_bytes()!=payload: raise ValueError('Immutable integrated capture differs')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(payload)
            accepted.append({'identity':observation['identity'],'status':'CAPTURED_CALL_TRACE',
                'artifact':bind(path,root),'frame_count':len(list(walk(tree))),
                'trace_identity_verified':True,'storage_trace_complete':False})
    if write_index:
        path=base/'trace_acquisition_train.json'
        previous=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        if isinstance(previous,dict): raise ValueError('Unexpected trace index schema')
        if any(r['identity'] not in rows for r in previous): raise ValueError('Nontrain acquisition index')
        archive=base/'trace_history'/(sha(path.read_bytes())+'.json') if path.exists() else None
        if archive: archive.parent.mkdir(parents=True,exist_ok=True); archive.write_bytes(path.read_bytes())
        ids={r['identity'] for r in accepted}
        write_json(path,accepted+[r for r in previous if r['identity'] not in ids])
    return accepted

if __name__=='__main__':
    print(json.dumps(integrate(),indent=2))
