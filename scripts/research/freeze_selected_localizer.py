"""Fit selected original110 model for deployment; never report in-sample scores."""
from pathlib import Path
import hashlib,json,pickle,subprocess
import selected_address_localizer as localizer
base=localizer.margin.learner.base
OUT=base.ROOT/'reports/localization_continuous/merge'


def main():
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=base.ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=base.ROOT,text=True).strip()
    if branch in ('main','master') or not branch:raise RuntimeError('Research branch required')
    model_path=OUT/'selected_model.pkl';config_path=OUT/'deployment_manifest.json'
    if model_path.exists() or config_path.exists():raise RuntimeError('Deployment artifact already frozen')
    base.install_offline_guard()
    parity=json.loads((OUT/'parity.json').read_text())
    if not parity.get('per_row_rankings_match'):raise RuntimeError('Integration parity required')
    for path,digest in parity['input_sha256'].items():
        if base.sha(Path(path))!=digest:raise RuntimeError('Parity dependency changed')
    rows,hashes=base.read_rows()
    raw=json.loads(base.MANIFEST.read_text(encoding='utf-8'))
    sources={r['filename']:r for r in raw['rows'] if r.get('status')=='ok'}
    for group in base.connected_groups(rows):
        for i in group:rows[i]['group_weight']=1/len(group)
    for row in rows:
        source=sources[row['row_id'].split(':',1)[1]]
        row.update(localizer.prepare(source.get('predictions') or [],str((source.get('cast') or {}).get('output_tail') or '')))
    bundle=localizer.fit(rows,list(range(len(rows))))
    payload=pickle.dumps(bundle,protocol=5)
    restored=pickle.loads(payload)
    # Behavioral roundtrip only; no correctness or training metrics computed.
    assert localizer.predict(bundle,rows[0])==localizer.predict(restored,rows[0])
    assert all(base.sha(p)==digest for p,digest in hashes.items())
    with model_path.open('xb') as handle:handle.write(payload)
    manifest={'status':'FROZEN_RESEARCH_DEPLOYMENT','training_population':'original110 only, 109 unique transactions','fit_records':len(rows),'method':list(localizer.CONFIG),'fitting_commit':commit,'branch':branch,'model_path':model_path.relative_to(base.ROOT).as_posix(),'model_sha256':hashlib.sha256(payload).hexdigest(),'code_sha256':parity['input_sha256'],'in_sample_metrics':None,'deployment_software_roundtrip':True,'development_oof_reference':parity['hits'],'development_status':'exploratory; 60percent top1 target unmet','fresh_batch_scored':False,'decoder_policy':'response-bound generic registry; literal selectors retained; unknown names empty; not verifiedABI','pickle_policy':'load only this self-produced artifact after checking pinned SHA256'}
    config_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':manifest['status'],'fit_records':len(rows),'model_sha256':manifest['model_sha256'],'in_sample_metrics':None,'fresh_batches_scored':0}))

if __name__=='__main__':main()
