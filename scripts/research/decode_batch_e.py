"""Acquire response-bound generic names for every observed selector, without labels."""
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
import hashlib,json,time
from fresh_evaluation_safety import billing_stop
from response_bound_decoder import decode
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/new_batches/batchE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def main():
    run=OUT/'capture_network_retry1';verification=json.loads((run/'verification.json').read_text())
    if verification['status']!='COLLECTED_40_UNSCORED':raise RuntimeError('40 verified rows required')
    registry=OUT/'registry';registry.mkdir(exist_ok=False)
    selectors=set()
    def visit(node):
        data=str(node.get('input') or '').lower()
        if data.startswith('0x') and len(data)>=10:selectors.add(data[:10])
        for child in node.get('calls') or []:visit(child)
    for row in verification['rows']:
        if not row['verified']:continue
        p=ROOT/row['raw_path']
        if sha(p)!=row['raw_sha256']:raise RuntimeError('Captured trace changed')
        visit(json.loads(p.read_text())['trace'])
    summary={'status':'RUNNING','selectors':len(selectors),'request_count':0,'rate_limit_hits':0,'mapping':{},'scoring_passes':0,'paid_spend_estimate_usd':0}
    write(registry/'acquisition_policy.json',{'selector_set':sorted(selectors),'source_verification_sha256':sha(run/'verification.json'),'labels_used':False,'policy':'all observed selectors; complete response-bound pages; lowest Keccak-valid numericID'})
    last=0.
    try:
        for selector in sorted(selectors):
            pages=[];url='https://www.4byte.directory/api/v1/signatures/?hex_signature='+selector
            while url:
                parsed=urlsplit(url)
                if parsed.scheme!='https' or parsed.netloc!='www.4byte.directory' or parsed.path!='/api/v1/signatures/':raise RuntimeError('Unapproved registry pagination URL')
                for attempt in range(4):
                    if time.monotonic()-last<1:time.sleep(1-(time.monotonic()-last))
                    summary['request_count']+=1;last=time.monotonic()
                    with (registry/'requests.jsonl').open('a',encoding='utf-8') as handle:handle.write(json.dumps({'event':'request_started','number':summary['request_count'],'url':url,'attempt':attempt})+'\n')
                    try:
                        with urlopen(Request(url,headers={'User-Agent':'FaultSeeker-research/1.0'}),timeout=45) as response:status=response.status;body=response.read().decode('utf-8')
                    except HTTPError as error:status=error.code;body=error.read().decode('utf-8',errors='replace')
                    try:data=json.loads(body)
                    except ValueError:data=None
                    message=data.get('error',{}) if isinstance(data,dict) and 'results' in data else body
                    if billing_stop(status,message):raise RuntimeError('Billing or quota stop')
                    if status==429:
                        summary['rate_limit_hits']+=1
                        if attempt==3:raise RuntimeError('Rate-limit retries exhausted')
                        time.sleep((2,4,8)[attempt]);continue
                    if status!=200 or not isinstance(data,dict) or not isinstance(data.get('results'),list):raise RuntimeError('Registry response unavailable')
                    break
                page={'url':url,'status':status,'retrieved_at':datetime.now(timezone.utc).isoformat(),'body':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest()}
                pages.append(page);write(registry/(selector+'_pages.json'),pages)
                url=data.get('next')
            result=decode(selector,pages)
            if result['status']=='invalid_response_binding':raise RuntimeError('Registry binding failed')
            summary['mapping'][selector]=result
            write(registry/'summary.json',summary)
            if len(summary['mapping'])%10==0:print(json.dumps({'selectors_resolved':len(summary['mapping']),'total':len(selectors),'requests':summary['request_count']}),flush=True)
        summary['status']='COMPLETE_UNSCORED'
    except Exception as error:
        summary['status']='STOPPED_UNSCORED';summary['reason_type']=type(error).__name__;summary['reason']=str(error) if isinstance(error,RuntimeError) else 'Public registry transport failed'
    finally:
        write(registry/'summary.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='mapping'}),flush=True)
if __name__=='__main__':main()
