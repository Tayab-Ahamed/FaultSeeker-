"""Measure gains only on identical authenticated TRAIN detector observations."""
import argparse
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark.paper_experiments import confusion_metrics
from benchmark.research_protocol import bind,read_bound,write_json,load_train
VARIANTS=('structural','repeated','full')

def paired_metrics(variants):
    if set(variants)!=set(VARIANTS):raise ValueError('Exactly three detector variants required')
    indexed={}
    for name,rows in variants.items():
        indexed[name]={r['identity']:r for r in rows}
        if len(indexed[name])!=len(rows):raise ValueError('Duplicate detector observation identity')
        if any(type(r['label']) is not bool or type(r['predicted_exploit']) is not bool for r in rows):raise ValueError('Boolean observed outcomes required')
    ids=sorted(set.intersection(*(set(rows) for rows in indexed.values())))
    if any(len({rows[k]['label'] for rows in indexed.values()})!=1 for k in ids):raise ValueError('Paired labels must agree')
    if not ids:return {'n':0,'paired_identities':[],'metrics':None,'scope':'Observed complete-case TRAIN comparison only','gains_pp':None}
    labels=[indexed['full'][k]['label'] for k in ids]
    metrics={name:confusion_metrics(labels,[rows[k]['predicted_exploit'] for k in ids]) for name,rows in indexed.items()}
    gains={name:(100*(metrics['full']['f1']-metrics[name]['f1']) if metrics['full']['f1'] is not None and metrics[name]['f1'] is not None else None) for name in ('structural','repeated')}
    return {'n':len(ids),'paired_identities':ids,'metrics':metrics,'scope':'Observed complete-case TRAIN comparison only','gains_pp':gains,'unpaired_exclusions':{name:sorted(set(rows)-set(ids)) for name,rows in indexed.items()}}

def run(run_id,root=ROOT):
    root=Path(root);base=root/'reports/cohort_rebuild_v2'
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{8}',run_id):raise ValueError('Invalid recorded run identifier')
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    train={r['chain']+':'+r['txn_hash'] for r in load_train(split,root)}
    log=json.loads((base/'experiments_log.json').read_text(encoding='utf-8'))
    variants={};bindings=[]
    for name in VARIANTS:
        matches=[e for e in log if e.get('run_id')==run_id and e.get('variant')==name and e.get('kind')=='scored-train']
        if len(matches)!=1:raise ValueError('Unique hash-bound executed variant event required')
        event=matches[0];data=json.loads(read_bound(event['evidence'],root))
        observations=data['observations']
        if any(r['identity'] not in train for r in observations):raise ValueError('Nontrain detector outcome')
        for row in observations:read_bound(row['capture_artifact'],root)
        variants[name]=observations;bindings.append(event['evidence'])
    result=paired_metrics(variants)
    result.update(source_run=run_id,inputs=bindings,frozen_split=bind(root/'benchmark/eval_split.json',root),eligible_train=len(train),paper_gains_pp={'structural':17,'repeated':29},limitations=['Paired cases reflect archive availability, not representative full-cohort outcomes','No held-out or full production system metrics','No threshold or weight tuning','No paired inference cost savings inferred from detector CPU timings'],heldout_used=False)
    if result['gains_pp'] is not None:
        result['delta_from_paper_pp']={name:(result['gains_pp'][name]-result['paper_gains_pp'][name] if result['gains_pp'][name] is not None else None) for name in ('structural','repeated')}
    out=base/'paired_gains'/run_id;out.mkdir(parents=True,exist_ok=True)
    source=out/'measurer.py.txt';current=Path(__file__).read_bytes()
    if source.exists() and source.read_bytes()!=current:raise ValueError('Immutable measurer snapshot differs')
    source.write_bytes(current);result['measurer_snapshot']=bind(source,root)
    path=out/'summary.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=result:raise ValueError('Immutable gain report differs')
    write_json(path,result);print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_id');run(parser.parse_args().run_id)
