"""Four-request, opt-in PublicNode call-trace probe for one frozen BSC train row.

All dispatched RPCs share the existing cumulative ledger. Captures preserve
parsed provider responses and cannot mutate the train acquisition registry.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from benchmark.research_protocol import bind,load_train,read_bound,sha,write_json
from scripts.probe_train_chain_traces import validate_trace,parity_call_tree,require_train
from scripts import replay_historical_opcodes as metering

TX='0x13d19809b19ac512da6d110764caee75e2157ea62cb70937c8d9471afcb061bf'
ENDPOINT='https://bsc-rpc.publicnode.com'
SOURCE='https://bsc.publicnode.com/'


def receipt_matches(actual,expected):
    if not isinstance(actual,dict):return False
    fields=('transactionHash','blockHash','blockNumber','transactionIndex','status','gasUsed','logs','contractAddress')
    return all(actual.get(k)==expected.get(k) for k in fields) and all(k in actual and k in expected for k in fields)


def probe(meter,rpc,rpc_binding,output,root=ROOT):
    root,output=Path(root),Path(output)
    if (rpc.get('chain')!='bsc' or rpc.get('chain_id')!=56 or rpc.get('txn_hash')!=TX
        or rpc.get('transaction',{}).get('hash')!=TX or rpc.get('receipt',{}).get('transactionHash')!=TX):
        raise ValueError('Canonical BSC train RPC identity mismatch')
    if output.exists() and any(output.iterdir()):raise ValueError('Immutable probe output already exists')
    output.mkdir(parents=True,exist_ok=True)
    summary={'identity':'bsc:'+TX,'endpoint':ENDPOINT,'endpoint_source':SOURCE,
        'created_at':datetime.now(timezone.utc).isoformat(),'requests':0,'maximum_requests':4,
        'attempts':[],'raw_requests':[],'status':'NO_TRACE','rpc_identity':rpc_binding,
        'record_format':'Parsed RPC JSON response envelopes; transport exception type only',
        'storage_trace_complete':False,'heldout_used':False,'no_automatic_retries':True}
    def request(method,params):
        if summary['requests']>=4:raise RuntimeError('Four-request cap reached before dispatch')
        summary['requests']+=1
        payload={'jsonrpc':'2.0','id':summary['requests'],'method':method,'params':params}
        record={'request':payload}
        try:record['response']=meter.forward(payload)
        except Exception as error:
            record['transport_error_type']=type(error).__name__
            status=getattr(error,'http_status',None)
            if type(status) is int and 100 <= status <= 599:
                record['http_status']=status
        path=output/'raw'/f"{summary['requests']}-{method}.json"
        write_json(path,record);summary['raw_requests'].append(bind(path,root))
        write_json(output/'probe.json',summary)
        return record.get('response',{})
    trace_allowed_before='trace_transaction' in metering.READ_METHODS
    metering.READ_METHODS.add('trace_transaction')
    try:
        chain=request('eth_chainId',[])
        if chain.get('result')!='0x38':
            summary['status']='WRONG_CHAIN' if chain.get('result') else 'CHAIN_ID_UNVERIFIED'
            return summary
        summary['chain_id_verified']=56
        for method,params in (('debug_traceTransaction',[TX,{'tracer':'callTracer','timeout':'15s'}]),('trace_transaction',[TX])):
            response=request(method,params);attempt={'method':method,'status':'UNAVAILABLE'}
            summary['attempts'].append(attempt)
            if response.get('error') or response.get('result') is None:continue
            value=response['result']
            try:
                tree=parity_call_tree(value,rpc['transaction'],rpc['receipt']) if method=='trace_transaction' else value
                validate_trace(tree,rpc['transaction'],rpc['receipt'])
            except (ValueError,TypeError,KeyError,AttributeError,IndexError) as error:
                attempt.update(status='INVALID_TRACE',error_type=type(error).__name__);continue
            current=request('eth_getTransactionReceipt',[TX])
            if current.get('error') or not receipt_matches(current.get('result'),rpc['receipt']):
                summary['status']='RECEIPT_UNVERIFIED';return summary
            artifact={'transaction_hash':TX,'chain':'bsc','chain_id':56,'method':method,'result':value,
                'validated_call_tree':tree,'rpc_identity':rpc_binding,'endpoint':ENDPOINT,
                'receipt_verification':summary['raw_requests'][-1],'raw_requests':list(summary['raw_requests']),
                'storage_trace_complete':False,'capture_version':'publicnode-train-call-trace-v1'}
            path=output/'capture.json';write_json(path,artifact)
            attempt.update(status='CAPTURED',artifact=bind(path,root))
            summary.update(status='CAPTURED',method=method,artifact=bind(path,root));return summary
        return summary
    finally:
        if not trace_allowed_before:metering.READ_METHODS.discard('trace_transaction')
        summary['accounting']=meter.summary()
        write_json(output/'probe.json',summary)


def run_live(root=ROOT,live=False):
    if not live:raise ValueError('Explicit --live required before any RPC dispatch')
    root=Path(root).resolve()
    split_path=root/'benchmark/eval_split.json';split=json.loads(split_path.read_text(encoding='utf-8'))
    require_train('bsc:'+TX,split)
    if sha((root/'benchmark/cohort_manifest.json').read_bytes())!=split['manifest_sha256']:
        raise ValueError('Frozen manifest digest mismatch')
    row=next(r for r in load_train(split,root) if r['chain']=='bsc' and r['txn_hash']==TX)
    rpc=json.loads(read_bound(row['rpc'],root))
    meter=metering.MeteredRPC(ENDPOINT,root/'data/research/spend_ledger.json',max_requests=4)
    return probe(meter,rpc,row['rpc'],root/'reports/cohort_rebuild_v2/bsc_trace_publicnode',root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    try:
        report=run_live(live=args.live)
        print(json.dumps({'status':report['status'],'requests':report['requests'],'accounting':report['accounting']}))
    except (ValueError,RuntimeError,OSError) as error:
        print('BSC train probe failed:',type(error).__name__);sys.exit(1)
