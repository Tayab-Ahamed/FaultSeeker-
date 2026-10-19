"""Free-tier-only RPC collection for frozen Batch E; never rank or score."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
import hashlib,json,os
from dotenv import dotenv_values
from fresh_evaluation_safety import RequestLedger,RequestGate,SafetyStop
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/new_batches/batchE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def main():
    frozen=json.loads((OUT/'freeze.json').read_text());cohort_path=OUT/'cohort.json'
    if sha(cohort_path)!=frozen['cohort_sha256']:raise RuntimeError('Frozen cohort changed')
    cohort=json.loads(cohort_path.read_text())
    for row in cohort['rows']:
        if sha(ROOT/row['source_path'])!=row['source_content_sha256']:raise RuntimeError('Frozen source changed')
    run=OUT/'capture';run.mkdir(exist_ok=False);(run/'raw').mkdir()
    values=dotenv_values(ROOT/'.env');endpoint=os.environ.get('DRPC_RPC_URL') or values.get('DRPC_RPC_URL') or ''
    key=os.environ.get('DRPC_API_KEY') or values.get('DRPC_API_KEY') or ''
    parsed=urlsplit(endpoint)
    if parsed.scheme!='https' or parsed.hostname!='lb.drpc.live':raise RuntimeError('Approved dRPC HTTPS endpoint unavailable')
    ledger=RequestLedger(run/'requests.jsonl');gate=RequestGate(ledger)
    def sanitize(value):
        if isinstance(value,str):
            value=value.replace(endpoint,'[RPC_URL_REDACTED]')
            return value.replace(key,'[API_KEY_REDACTED]') if key else value
        if isinstance(value,dict):return {k:sanitize(v) for k,v in value.items()}
        if isinstance(value,list):return [sanitize(v) for v in value]
        return value
    def rpc(method,params,index):
        def transport():
            req=Request(endpoint,data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json'})
            try:
                with urlopen(req,timeout=60) as response:status=response.status;body=response.read()
            except HTTPError as error:status=error.code;body=error.read()
            try:result=json.loads(body)
            except (ValueError,UnicodeError):result={'error':{'message':body.decode('utf-8',errors='replace')}}
            return status,sanitize(result)
        status,result=gate.call(transport,method=method,row_index=index)
        return {'http_status':status,'body':result}
    summary={'status':'RUNNING','cohort_sha256':frozen['cohort_sha256'],'rows':[],'verified_count':0,'scoring_passes':0,'paid_spend_estimate_usd':0,'free_tier_only':True}
    try:
        chain=rpc('eth_chainId',[],0)
        write(run/'chain_identity.json',chain)
        if chain['body'].get('result')!='0x1':raise SafetyStop('Ethereum chain identity not verified')
        for index,label in enumerate(cohort['rows'],1):
            tx=label['transaction_hash'];responses={}
            for method,params in [('eth_getTransactionByHash',[tx]),('eth_getTransactionReceipt',[tx]),('debug_traceTransaction',[tx,{'tracer':'callTracer','timeout':'15s'}])]:
                responses[method]=rpc(method,params,index)
            transaction=responses['eth_getTransactionByHash']['body'].get('result');receipt=responses['eth_getTransactionReceipt']['body'].get('result');trace=responses['debug_traceTransaction']['body'].get('result')
            reasons=[]
            if not isinstance(transaction,dict) or str(transaction.get('hash','')).lower()!=tx:reasons.append('transaction_unresolved_or_hash_mismatch')
            if not isinstance(receipt,dict) or str(receipt.get('transactionHash','')).lower()!=tx:reasons.append('receipt_unresolved_or_hash_mismatch')
            elif receipt.get('status')!='0x1':reasons.append('successful_receipt_not_established')
            if not isinstance(trace,dict) or not trace.get('to'):reasons.append('call_trace_unavailable_or_invalid')
            raw=run/'raw'/(tx+'.json');write(raw,{'transaction_hash':tx,'transaction':transaction,'receipt':receipt,'trace':trace,'responses':responses})
            summary['rows'].append({'transaction_hash':tx,'verified':not reasons,'exclusion_reasons':reasons,'raw_path':str(raw.relative_to(ROOT)).replace('\\','/'),'raw_sha256':sha(raw)})
            summary['verified_count']+=int(not reasons)
            write(run/'verification.json',summary)
            print(json.dumps({'collected_rows':len(summary['rows']),'verified':summary['verified_count']}),flush=True)
            if summary['verified_count']==40:break
        summary['status']='COLLECTED_40_UNSCORED' if summary['verified_count']==40 else 'INSUFFICIENT_VERIFIED_DATA_UNSCORED'
    except SafetyStop as error:
        summary['status']='STOPPED_SAFETY_UNSCORED';summary['reason']=str(error)
    finally:
        events=[json.loads(line) for line in (run/'requests.jsonl').read_text().splitlines()] if (run/'requests.jsonl').exists() else []
        summary['request_count']=sum(e['event']=='request_started' for e in events);summary['rate_limit_hits']=sum(e['event']=='rate_limited' for e in events)
        write(run/'verification.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
