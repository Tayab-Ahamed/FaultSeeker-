"""Reproduce only original110 development predictions for integration parity."""
import hashlib,json
from pathlib import Path
import selected_address_localizer as localizer
base=localizer.margin.learner.base
OUT=base.ROOT/'reports/localization_continuous/merge'


def main():
    base.install_offline_guard()
    destination=OUT/'parity.json'
    if destination.exists():raise RuntimeError('Integration result already recorded')
    rows,hashes=base.read_rows()
    sources=json.loads(base.MANIFEST.read_text(encoding='utf-8'))
    raw={r['filename']:r for r in sources['rows'] if r.get('status')=='ok'}
    groups=base.connected_groups(rows);folds=base.assign_folds(groups)
    for group in groups:
        for i in group:rows[i]['group_weight']=1/len(group)
    for row in rows:
        source=raw[row['row_id'].split(':',1)[1]]
        row.update(localizer.prepare(source.get('predictions') or [],str((source.get('cast') or {}).get('output_tail') or '')))
    dependencies=[Path(__file__),Path(localizer.__file__),Path(localizer.margin.__file__),Path(localizer.margin.learner.__file__),Path(localizer.margin.behavior.__file__),Path(base.__file__),Path(localizer.coverage.__file__),Path(localizer.topology.__file__),Path(localizer.lexical.__file__),base.ROOT/'scripts/research/names_semantics.py',base.ROOT/'faultseeker/function_analysis/function_ranker.py',base.ROOT/'faultseeker/function_analysis/candidate_generation.py',OUT/'PROTOCOL.md']
    for p in dependencies:hashes[p]=base.sha(p)
    predictions=[None]*len(rows)
    for fold in range(5):
        train=[i for i in range(len(rows)) if folds[i]!=fold]
        test=[i for i in range(len(rows)) if folds[i]==fold]
        bundle=localizer.fit(rows,train)
        for i in test:predictions[i]=localizer.predict(bundle,rows[i])
        print('Completed integration fold',fold,flush=True)
    reference=base.ROOT.parent/'FaultSeeker--learned/reports/localization_continuous/lane_c/results12.json'
    saved=json.loads(reference.read_text(encoding='utf-8'))['variants']['basic_svc_10.0']
    if predictions!=saved['oof_rankings']:raise RuntimeError('Per-row parity failed; do not promote')
    ranks=[base.first_hit(p,r['targets']) for p,r in zip(predictions,rows)]
    assert ranks==saved['oof_ranks']
    assert all(base.sha(p)==h for p,h in hashes.items())
    result={'kind':'integration_parity_on_spent_development_data','exploratory':True,'per_row_rankings_match':True,'records':len(rows),'metrics':base.metrics(ranks),'hits':base.hit_counts(ranks),'oof_ranks':ranks,'oof_rankings':predictions,'folds':folds,'reference_sha256':base.sha(reference),'input_sha256':{str(p):h for p,h in hashes.items()},'network_requests':0,'fresh_batches_read':0}
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Per-row parity PASS',result['hits'],flush=True)

if __name__=='__main__':main()
