"""Frozen grouped OOF evaluation for candidate expansion."""
import itertools
import json
from pathlib import Path
from scripts.research import address_ranking_phase1 as base
from scripts.research.address_coverage_lane_a import extract_candidates, rank_candidates

OUT = base.ROOT / 'reports/localization_continuous/lane_a'

def grid():
    return [dict(kind='train_fold_grid', calls=c, delegate=d, references=r)
            for c,d,r in itertools.product((0.,.25,.5,1.), repeat=3)]

def fit(rows, indices):
    return max(grid(), key=lambda config: tuple(base.hit_counts([
        base.first_hit(rank_candidates(rows[i]['coverage_evidence'],config), rows[i]['targets'])
        for i in indices])))

def run():
    base.install_offline_guard()
    destination = OUT/'results.json'
    if destination.exists():
        raise RuntimeError('Refusing to overwrite frozen result')
    rows, fingerprints = base.read_rows()
    manifest = json.loads(base.MANIFEST.read_text(encoding='utf-8'))
    source = sorted([r for r in manifest['rows'] if r.get('status')=='ok'],key=lambda r:(r['txn_hash'],r['filename']))
    for row, raw in zip(rows,source):
        row['coverage_evidence'] = extract_candidates(raw.get('predictions') or [],str((raw.get('cast') or {}).get('output_tail') or ''))
    groups = base.connected_groups(rows)
    folds = base.assign_folds(groups)
    baseline = [base.first_hit([r['address'] for r in row['evidence']],row['targets']) for row in rows]
    assert base.hit_counts(baseline) == [55,68,76]
    assert sum(r is not None for r in baseline)==84
    unique = []
    seen = set()
    for i,row in enumerate(rows):
        if row['tx'] not in seen:
            unique.append(i)
            seen.add(row['tx'])
    results = {}
    for variant in ['call_append','reference_append','train_fold_grid']:
        ranks = [None]*len(rows)
        configurations = []
        for fold in range(5):
            train = [i for i in range(len(rows)) if folds[i]!=fold]
            test = [i for i in range(len(rows)) if folds[i]==fold]
            config = fit(rows,train) if variant=='train_fold_grid' else {'kind':variant}
            configurations.append(dict(fold=fold,config=config,train=train,test=test))
            for i in test:
                ranks[i] = base.first_hit(rank_candidates(rows[i]['coverage_evidence'],config),rows[i]['targets'])
        delta = [a-b for a,b in zip(base.hit_counts(ranks),base.hit_counts(baseline))]
        ud = [a-b for a,b in zip(base.hit_counts([ranks[i] for i in unique]),base.hit_counts([baseline[i] for i in unique]))]
        results[variant] = dict(metrics=base.metrics(ranks),unique109_metrics=base.metrics([ranks[i] for i in unique]),delta=delta,unique_delta=ud,
          eligible=min(delta)>=0 and max(delta)>0 and min(ud)>=0 and max(ud)>0,
          coverage=sum(r is not None for r in ranks),oof_ranks=ranks,folds=configurations)
    for p in [Path(__file__),OUT/'PROTOCOL.md',base.ROOT/'scripts/research/address_coverage_lane_a.py']:
        fingerprints[p]=base.sha(p)
    result = dict(exploratory=True,baseline=base.metrics(baseline),baseline_coverage=84,groups=len(groups),variants=results,
      rows=[dict(row_id=r['row_id'],fold=folds[i],baseline_rank=baseline[i],baseline_candidates=len(r['evidence']),expanded_candidates=len(r['coverage_evidence']),candidates=r['coverage_evidence']) for i,r in enumerate(rows)],
      input_sha256={str(p.relative_to(base.ROOT)):h for p,h in fingerprints.items()},network_calls=0,fresh_batches_read=0)
    assert all(base.sha(p)==h for p,h in fingerprints.items())
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({v:dict(hits=base.hit_counts(r['oof_ranks']),coverage=r['coverage'],eligible=r['eligible']) for v,r in results.items()}))

if __name__=='__main__':
    run()
