"""Fixed exploratory fold-local learners. Never fit or report a full-data model."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import address_ranking_phase1 as base

OUT = base.ROOT / 'reports/localization_continuous/lane_c'
FEATURES = ('best_reciprocal','reciprocal_sum','structural','terminal_fanout','delegate_neighbor')
VARIANTS = tuple((kind, c) for kind in ('pointwise','pairwise') for c in (.1,1.,10.)) + (('forest',2),('forest',4),('hist',7))

def matrix(row):
    return np.asarray([[float(e[k]) for k in FEATURES]+[1/(j+1)] for j,e in enumerate(row['evidence'])], dtype=float).reshape(-1,6)

def training_data(rows, train, pairwise):
    x,y,w = [],[],[]
    for i in train:
        a = matrix(rows[i])
        labels = [int(e['address'] in rows[i]['targets']) for e in rows[i]['evidence']]
        if pairwise:
            pairs = [(p,n) for p,v in enumerate(labels) if v for n,z in enumerate(labels) if not z]
            for p,n in pairs:
                x.extend([a[p]-a[n],a[n]-a[p]]); y.extend([1,0]); w.extend([1/(2*len(pairs))]*2)
        else:
            x.extend(a); y.extend(labels); w.extend([1/max(1,len(a))]*len(a))
    return np.asarray(x),np.asarray(y),np.asarray(w)

def fit(rows, train, variant):
    kind,param=variant
    x,y,w=training_data(rows,train,kind=='pairwise')
    if kind in ('pointwise','pairwise'):
        model=make_pipeline(StandardScaler(),LogisticRegression(C=param,max_iter=1000,random_state=base.SEED))
        model.fit(x,y,logisticregression__sample_weight=w)
    else:
        model=(RandomForestClassifier(n_estimators=200,max_depth=param,min_samples_leaf=10,random_state=base.SEED,n_jobs=1) if kind=='forest' else HistGradientBoostingClassifier(max_leaf_nodes=7,max_iter=60,l2_regularization=10,random_state=base.SEED))
        model.fit(x,y,sample_weight=w)
    return model

def predict(model,row):
    x=matrix(row)
    if not len(x): return []
    scores=model.predict_proba(x)[:,1]
    return [row['evidence'][i]['address'] for i in sorted(range(len(x)),key=lambda i:(-scores[i],i))]

def main():
    base.install_offline_guard()
    destination=OUT/'results.json'
    if destination.exists(): raise RuntimeError('Do not overwrite recorded experiment')
    rows,fingerprints=base.read_rows()
    folds=base.assign_folds(base.connected_groups(rows))
    baseline=[base.first_hit([e['address'] for e in r['evidence']],r['targets']) for r in rows]
    report={'protocol_sha256':base.sha(OUT/'PROTOCOL.md'),'script_sha256':base.sha(Path(__file__)), 'features':list(FEATURES)+['candidate_position_reciprocal'],'baseline':base.hit_counts(baseline),'variants':{},'fold_for':folds,'exploratory':True}
    for variant in VARIANTS:
        name=f'{variant[0]}_{variant[1]}'
        predictions=[None]*len(rows)
        audits=[]
        for fold in range(5):
            train=[i for i in range(len(rows)) if folds[i]!=fold]
            test=[i for i in range(len(rows)) if folds[i]==fold]
            model=fit(rows,train,variant)
            for i in test: predictions[i]=predict(model,rows[i])
            # Identity fields do not enter the feature matrix.
            changed=copy.deepcopy(rows[test[0]])
            changed.update(tx='changed',incident='changed',targets=['changed'],urls=['changed'],row_id='changed')
            assert np.array_equal(matrix(changed),matrix(rows[test[0]]))
            assert predict(model,changed)==predictions[test[0]]
            # Retrain with all heldout labels changed; output must be identical.
            poisoned=copy.deepcopy(rows)
            for i in test: poisoned[i]['targets']=['heldout-label-poison']
            alternate=fit(poisoned,train,variant)
            assert all(predict(alternate,rows[i])==predictions[i] for i in test)
            audits.append({'fold':fold,'train':train,'test':test,'heldout_label_independence':True,'identity_invariance':True})
        ranks=[base.first_hit(p,r['targets']) for p,r in zip(predictions,rows)]
        report['variants'][name]={'hits':base.hit_counts(ranks),'metrics':base.metrics(ranks),'oof_rankings':predictions,'oof_ranks':ranks,'audits':audits}
        print(name,base.hit_counts(ranks),flush=True)
    assert all(base.sha(p)==h for p,h in fingerprints.items())
    report['input_sha256']={p.relative_to(base.ROOT).as_posix():h for p,h in fingerprints.items()}
    destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
