"""Read-only verification of frozen outputs. Never runs a ranker or scorer."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/new_batches/batchE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    score=json.loads((OUT/'scoring.json').read_text());runtime=json.loads((OUT/'runtime_freeze.json').read_text());freeze=json.loads((OUT/'freeze.json').read_text())
    assert score['scoring_runs']==1 and (OUT/'score_started.lock').exists()
    assert sha(OUT/'cohort.json')==freeze['cohort_sha256']==score['cohort_sha256']
    for path,digest in runtime['input_sha256'].items():assert sha(Path(path))==digest,path
    assert len(score['rows'])==40 and len({r['transaction_hash'] for r in score['rows']})==40
    ranks=[r['address_rank'] for r in score['rows']]
    for k in (1,3,5):
        item=score['metrics'][f'R@{k}'];h=sum(r is not None and r<=k for r in ranks);assert item['hits']==h and item['n']==40 and item['recall']==h/40
        z=1.959963984540054;den=1+z*z/40;mid=(h/40+z*z/80)/den;half=z*math.sqrt((h/40)*(1-h/40)/40+z*z/(4*40*40))/den
        assert all(abs(a-b)<1e-12 for a,b in zip(item['wilson95'],[mid-half,mid+half]))
    rpc=[]
    for folder in ['capture','capture_network_retry1']:
        rpc.extend(json.loads(line) for line in (OUT/folder/'requests.jsonl').read_text().splitlines())
    registry=[json.loads(line) for line in (OUT/'registry/requests.jsonl').read_text().splitlines()]
    assert sum(e['event']=='request_started' for e in rpc)==score['rpc_requests']==122
    assert len(registry)==score['registry_requests']==323
    print(json.dumps({'verification':'PASS','metrics':score['metrics'],'rpc_dispatches_including_one_dns_failure':122,'registry_requests':323,'ranking_or_scoring_runs_in_this_verifier':0},indent=2))
if __name__=='__main__':main()
