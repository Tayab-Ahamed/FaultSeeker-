"""Freeze source-backed address labels using cached public sources only."""
import gzip,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/new_batches/batchE'
ADDRESS=re.compile(r'0x[0-9a-fA-F]{40}(?![0-9a-fA-F])')
TX=re.compile(r'0x[0-9a-fA-F]{64}(?![0-9a-fA-F])')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized(value):return re.sub('[^a-z0-9]','',str(value).lower())
def main():
    if (OUT/'cohort.json').exists():raise RuntimeError('Cohort already frozen')
    txs=set();addresses=set();incidents=set();stems=set();inputs={}
    for p in sorted((ROOT/'benchmark/original_faultseeker/ground_truth').glob('*.json')):
        d=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=sha(p);txs.add(p.stem.lower());incidents.add(normalized(d.get('name','')))
        for k,v in (d.get('location') or {}).items():addresses.update(a.lower() for a in ADDRESS.findall(str(k)+' '+str(v)))
    for f in ['batchA_candidates.json','batchB/batchB_candidates.json','batchC/batchC_candidates.json','batchD/batchD_candidates.json']:
        p=ROOT/'reports/new_batches'/f;d=json.loads(p.read_text());inputs[str(p.relative_to(ROOT))]=sha(p)
        for r in d['rows']:
            txs.add(r['transaction_hash'].lower());addresses.add(str(r.get('vulnerable_contract_address') or r.get('vulnerable_contract') or '').lower())
            stem=Path(r.get('source_path','')).stem.removesuffix('_exp');stems.add(normalized(stem));incidents.add(normalized(r.get('incident_name') or stem))
    index=ROOT/'reports/cohort_rebuild_v2/poc_sources.json';inputs[str(index.relative_to(ROOT))]=sha(index)
    rows=[];rejections=[];seen_tx=set();seen_address=set();seen_incident=set()
    for source in sorted(json.loads(index.read_text())['sources'],key=lambda s:s['url']):
        if '.sol' not in source['url'] or source.get('http_status')!=200:continue
        p=ROOT/source['file'];packed=p.read_bytes()
        if hashlib.sha256(packed).hexdigest()!=source['sha256']:raise RuntimeError('Cached compressed hash mismatch')
        body=gzip.decompress(packed) if source.get('compressed') else packed
        if hashlib.sha256(body).hexdigest()!=source['body_sha256']:raise RuntimeError('Cached source hash mismatch')
        text=body.decode('utf-8',errors='replace')
        if not re.search(r'createSelectFork\(\s*"(?:mainnet|eth|ethereum)"',text):continue
        vs=[];ts=[]
        for n,line in enumerate(text.splitlines()[:100],1):
            if re.search(r'vulnerable\s*contract\s*:',line,re.I):vs.extend((a.lower(),n,line) for a in ADDRESS.findall(line))
            if re.search(r'attack\s*tx\s*:',line,re.I):ts.extend((t.lower(),n,line) for t in TX.findall(line))
        va=list(dict.fromkeys(v[0] for v in vs));ta=list(dict.fromkeys(t[0] for t in ts));name=Path(source['url']).stem.removesuffix('_exp');incident=normalized(name)
        reason=None
        if len(va)!=1 or len(ta)!=1:reason='missing_or_ambiguous_explicit_headers'
        elif va[0] in addresses or ta[0] in txs or incident in incidents or incident in stems:reason='spent_incident_contract_or_transaction'
        elif va[0] in seen_address or ta[0] in seen_tx or incident in seen_incident:reason='duplicate_new_incident_contract_or_transaction'
        if reason:rejections.append({'source_url':source['url'],'reason':reason});continue
        seen_tx.add(ta[0]);seen_address.add(va[0]);seen_incident.add(incident)
        target=next(v for v in vs if v[0]==va[0]);transaction=next(v for v in ts if v[0]==ta[0])
        source_dir=OUT/'sources';source_dir.mkdir(exist_ok=True);local=source_dir/(source['body_sha256']+'.sol');local.write_bytes(body)
        rows.append({'chain':'eth','incident_name':name,'transaction_hash':ta[0],'target_address':va[0],'label_type':'explicit_public_PoC_vulnerable_contract_header','source_url':source['url'],'source_content_sha256':source['body_sha256'],'source_path':str(local.relative_to(ROOT)).replace('\\','/'),'source_commit':None,'target_evidence':{'line':target[1],'quote':target[2]},'transaction_evidence':{'line':transaction[1],'quote':transaction[2]},'function_target':None,'independent_root_cause_adjudication':False})
    if len(rows)<40:raise RuntimeError('Fewer than40 eligible source labels; do not score')
    deployment=OUT.parent.parent/'localization_continuous/merge/deployment_manifest.json';inputs[str(deployment.relative_to(ROOT))]=sha(deployment)
    cohort={'status':'LABELS_FROZEN_BEFORE_RPC_AND_RANKING','endpoint':'distinct_address','primary_verified_count_required':40,'eligible_labels':len(rows),'rows':rows,'rejections':rejections,'exclusion_input_sha256':inputs,'ranker_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'model_manifest_sha256':sha(deployment),'protocol_sha256':sha(OUT/'PROTOCOL.md'),'selection':'first40 RPC-verified in fixed URL order; all remaining eligible labels are reserves','limitations':['PoC target headers, not independently adjudicated root causes','Cached main-branch source bytes SHA-pinned, upstream commit unavailable','Function targets unavailable; no exact-selector metric']}
    payload=(json.dumps(cohort,sort_keys=True,indent=2)+'\n').encode();(OUT/'cohort.json').write_bytes(payload)
    (OUT/'freeze.json').write_text(json.dumps({'cohort_sha256':hashlib.sha256(payload).hexdigest(),'label_rows':len(rows),'ranking_passes':0,'rpc_requests':0,'ranker_commit':cohort['ranker_commit']},indent=2)+'\n')
    print(json.dumps({'frozen_source_labels':len(rows),'required_verified':40,'rpc_requests':0,'rankings':0,'cohort_sha256':hashlib.sha256(payload).hexdigest()}))
if __name__=='__main__':main()
