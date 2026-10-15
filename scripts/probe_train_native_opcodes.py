"""Bounded direct-node historical TRAIN opcode acquisition; no Anvil proof path."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.modules['readline']=None
from benchmark.research_protocol import load_train,read_bound,bind
from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
from faultseeker.utils.rpc_provider import normalize_trace_node
from scripts.probe_train_chain_traces import validate_trace
from scripts.replay_historical_opcodes import MeteredRPC

TX='0x534b84f657883ddc1b66a314e8b392feb35024afdec61dfe8e7c510cfac1a098'
ENDPOINT='https://rpc.gnosischain.com'
CONFIG={'disableMemory':True,'disableStack':False,'disableStorage':False,'timeout':'15s'}

def integer(value):
    if isinstance(value,bool):raise ValueError('Boolean is not RPC integer')
    return value if isinstance(value,int) else int(value,16)

def validate_native(chain_id,transaction,receipt,call,opcode,expected_hash):
    if integer(chain_id)!=100:raise ValueError('Historical endpoint chain mismatch')
    if (transaction.get('hash','').lower()!=expected_hash.lower()
            or receipt.get('transactionHash','').lower()!=expected_hash.lower()
            or transaction.get('blockHash')!=receipt.get('blockHash')
            or transaction.get('blockNumber')!=receipt.get('blockNumber')
            or receipt.get('status')!='0x1'):
        raise ValueError('Historical transaction/receipt identity mismatch')
    if transaction.get('chainId') is not None and integer(transaction['chainId'])!=100:
        raise ValueError('Historical transaction chain mismatch')
    validate_trace(call,transaction,receipt)
    if call.get('gasUsed') is not None and integer(call['gasUsed'])!=integer(receipt['gasUsed']):
        raise ValueError('Call trace receipt gas mismatch')
    if (not isinstance(opcode,dict) or opcode.get('failed') is not False or opcode.get('error')
            or opcode.get('truncated') or not isinstance(opcode.get('structLogs'),list)
            or not opcode['structLogs']):
        raise ValueError('Successful nonempty complete native opcode trace required')
    if opcode.get('gas') is not None and integer(opcode['gas'])!=integer(receipt['gasUsed']):
        raise ValueError('Native opcode receipt gas mismatch')
    logs=opcode['structLogs'];counts=Counter(str(x.get('op','')).upper() for x in logs)
    canonical=normalize_trace_node(call);owners={}
    def walk(node,owner=None):
        kind=node['call_type'];storage=owner if kind in ('DELEGATECALL','CALLCODE') else node['callee'].lower()
        owners[node['call_id']]=storage
        for child in node['children']:walk(child,storage)
    walk(canonical)
    if sum(counts[x] for x in ('CALL','STATICCALL','DELEGATECALL','CALLCODE','CREATE','CREATE2'))!=len(owners)-1:
        raise ValueError('Native opcode/canonical call frame count mismatch')
    normalized=normalize_opcode_storage_trace(logs,canonical)
    if (normalized.get('normalization_complete') is not True
            or len(normalized['storage_reads'])!=counts['SLOAD']
            or len(normalized['storage_events'])!=counts['SSTORE']):
        raise ValueError('Native storage normalization is incomplete')
    for entry in normalized['storage_reads']+normalized['storage_events']:
        if owners.get(entry['call_id'])!=entry['address'].lower():
            raise ValueError('Native storage owner mapping mismatch')
    return {'normalization':normalized,'opcode_count':len(logs),'canonical_frame_count':len(owners),
            'sload_count':counts['SLOAD'],'sstore_count':counts['SSTORE'],
            'frame_storage_owners':owners,'identity_and_receipt_verified':True,
            'proof_kind':'direct_historical_node_trace_with_bound_call_tree'}

def validate_recorded_native_capture(path,expected_hash,root=ROOT):
    """Revalidate native node evidence; no synthetic Anvil prefix substitute."""
    root=Path(root)
    raw=Path(path).read_bytes()
    capture=json.loads(gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw)
    if (capture.get('capture_version')!='direct-native-historical-opcode-v1'
            or capture.get('chain')!='gnosis' or capture.get('transaction_hash')!=expected_hash):
        raise ValueError('Native capture version/identity mismatch')
    rpc=json.loads(read_bound(capture['rpc_identity'],root))
    if capture['transaction']!=rpc['transaction']:
        raise ValueError('Native transaction differs from bound RPC evidence')
    for field in ('transactionHash','blockHash','blockNumber','transactionIndex','gasUsed','status'):
        if capture['canonical_receipt'].get(field)!=rpc['receipt'].get(field):
            raise ValueError('Native receipt differs from bound RPC evidence')
    call_capture=json.loads(gzip.decompress(read_bound(capture['bound_call_capture'],root)))
    if (call_capture.get('rpc_identity')!=capture['rpc_identity']
            or call_capture['raw_trace']['call']!=capture['raw_trace']['call']):
        raise ValueError('Native canonical call tree binding mismatch')
    proof=validate_native(100,rpc['transaction'],capture['canonical_receipt'],
                          capture['raw_trace']['call'],capture['raw_trace']['opcode'],expected_hash)
    if proof['normalization']!=capture['normalization']:
        raise ValueError('Native stored normalization differs from raw opcode normalization')
    if {k:v for k,v in proof.items() if k!='normalization'}!=capture['native_proof']:
        raise ValueError('Native proof differs from independently recomputed proof')
    return proof


def run(output,max_requests=6):
    if not 1<=max_requests<=6:raise ValueError('Native probe request cap must be 1..6')
    split=json.loads((ROOT/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    row=next((r for r in load_train(split,ROOT) if r['chain']=='gnosis' and r['txn_hash']==TX),None)
    if row is None:raise ValueError('Native target is not frozen TRAIN')
    index_path=ROOT/'reports/cohort_rebuild_v2/chain_trace_probe/INTEGRATION.json'
    index=json.loads(index_path.read_text(encoding='utf-8'))
    bindings=[b for b in index['captures'] if b['path'].endswith('gnosis-'+TX+'.json.gz')]
    if len(bindings)!=1:raise ValueError('Unique bound Gnosis call tree required')
    call_capture=json.loads(gzip.decompress(read_bound(bindings[0],ROOT)))
    if (call_capture.get('transaction_hash')!=TX or call_capture.get('chain')!='gnosis'
            or call_capture.get('rpc_identity')!=row['rpc']):
        raise ValueError('Gnosis call capture identity/binding mismatch')
    rpc=json.loads(read_bound(row['rpc'],ROOT));tx=rpc['transaction'];receipt=rpc['receipt']
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must stay inside workspace')
    output.mkdir(parents=True,exist_ok=True)
    report_path=output/'probe.json'
    if report_path.exists():raise ValueError('Immutable probe exists; no blind rerun')
    meter=MeteredRPC(ENDPOINT,ROOT/'data/research/spend_ledger.json',max_requests=max_requests)
    report={'identity':'gnosis:'+TX,'endpoint':ENDPOINT,'rpc_identity':row['rpc'],
            'bound_call_capture':bindings[0],'call_index':bind(index_path,ROOT),
            'capture_path':'direct native historical node; not Anvil prefix replay',
            'requests':[],'status':'NOT_DISPATCHED','billing_confirmed':False}
    def request(method,params):
        payload={'jsonrpc':'2.0','id':len(report['requests'])+1,'method':method,'params':params}
        observation={'request':payload};report['requests'].append(observation)
        response=meter.forward(payload)
        # Fixed public endpoint only. Store true RPC responses, never exception text.
        path=output/('response-%02d.json.gz'%len(report['requests']))
        path.write_bytes(gzip.compress(json.dumps(response,ensure_ascii=False).encode('utf-8'),mtime=0))
        observation['response']=bind(path,ROOT)
        if response.get('error') or response.get('result') is None:
            observation['rpc_error_code']=(response.get('error') or {}).get('code')
            raise ValueError('Native RPC response unavailable')
        return response['result']
    try:
        chain=request('eth_chainId',[])
        if integer(chain)!=100:raise ValueError('Public native chain mismatch')
        opcode=request('debug_traceTransaction',[TX,CONFIG])
        actual_receipt=request('eth_getTransactionReceipt',[TX])
        for field in ('transactionHash','blockHash','blockNumber','transactionIndex','gasUsed','status'):
            if actual_receipt.get(field)!=receipt.get(field):raise ValueError('Live/bound receipt mismatch')
        proof=validate_native(chain,tx,actual_receipt,call_capture['raw_trace']['call'],opcode,TX)
        capture={'capture_version':'direct-native-historical-opcode-v1','transaction_hash':TX,'chain':'gnosis',
                 'transaction':tx,'canonical_receipt':actual_receipt,'raw_trace':{'call':call_capture['raw_trace']['call'],'opcode':opcode},
                 'normalization':proof['normalization'],'native_proof':{k:v for k,v in proof.items() if k!='normalization'},
                 'rpc_identity':row['rpc'],'bound_call_capture':bindings[0]}
        path=output/(TX+'.json.gz');path.write_bytes(gzip.compress(json.dumps(capture).encode('utf-8'),mtime=0))
        report.update(status='CAPTURED_VERIFIED_NATIVE_OPCODES',capture=bind(path,ROOT),proof=capture['native_proof'])
    except Exception as exc:
        report.update(status='NATIVE_OPCODES_UNAVAILABLE',error_type=type(exc).__name__)
    finally:
        report['meter']=meter.summary()
        report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'requests':meter.count,'capture':report.get('capture')},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--max-requests',type=int,default=6);parser.add_argument('--output',type=Path,default=ROOT/'reports/cohort_rebuild_v2/native_opcode_probe');args=parser.parse_args()
    if not args.live:parser.error('Explicit --live required; no request dispatched')
    run(args.output,args.max_requests)
