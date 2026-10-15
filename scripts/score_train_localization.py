"""Score explicit actual production function ranks on source-linked TRAIN only."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from benchmark.research_protocol import bind,read_bound,load_train,write_json,append_experiment

def function_rank(predictions,targets):
    seen=set()
    found=[]
    for position,row in enumerate(predictions,1):
        if row['rank']!=position: raise ValueError('Rank positions must be explicit and consecutive')
        key=(row['code_address'].lower(),(row.get('selector') or row.get('function','')).lower())
        if key in seen: raise ValueError('Duplicate ranked function identity')
        seen.add(key)
        if key in targets: found.append(position)
    return min(found) if found else None

def score(run_id,root=ROOT):
    root=Path(root);base=root/'reports/cohort_rebuild_v2'
    protocol=base/'localization_train_protocol.json'
    config=json.loads(protocol.read_text(encoding='utf-8'))
    targets=json.loads(read_bound(config['targets'],root))
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    train={r['chain']+':'+r['txn_hash'] for r in load_train(split,root)}
    run=base/'production_runs'/run_id
    if run.parent!=base/'production_runs' or not run.is_dir(): raise ValueError('Invalid production run')
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    if summary['heldout_used'] is not False or summary['final_exam_dispatched'] is not False: raise ValueError('Not a train-only run')
    observed=[];missing=[]
    for case in targets['cases']:
        key=case['identity']
        if key not in train: raise ValueError('Source target outside frozen train')
        if case['status']!='FUNCTION_IDENTITY_VERIFIED': continue
        expected={(f['code_address'].lower(),f['selector'].lower()) for f in case['function_evidence']}
        chain,tx=key.split(':',1);path=run/(chain+'-'+tx+'.json')
        if not path.exists(): missing.append({'identity':key,'reason':'No production observation'});continue
        prediction=json.loads(path.read_text(encoding='utf-8'))
        if prediction['identity']!=key: raise ValueError('Production identity mismatch')
        rank=function_rank(prediction['ranking']['ranked_functions'],expected)
        observed.append({'identity':key,'rank':rank,'reciprocal_rank':1/rank if rank else 0,
            'prediction':bind(path,root),'target_identities':[list(x) for x in sorted(expected)]})
    n=len(observed)
    metrics={'n':n,'top1':sum(r['rank']==1 for r in observed)/n,'top5':sum(r['rank'] is not None and r['rank']<=5 for r in observed)/n,'mrr':sum(r['reciprocal_rank'] for r in observed)/n} if n else None
    out=run/'source_localization.json'
    if out.exists(): raise ValueError('Immutable score already exists')
    report={'scope':'Deterministic count-ranked TRAIN function localization only','protocol':bind(protocol,root),'production_summary':bind(run/'summary.json',root),'metrics':metrics,'observations':observed,'missing':missing,'heldout_used':False,'multi_agent_stage3_executed':False}
    write_json(out,report)
    append_experiment(base/'experiments_log.json',split,{'kind':'scored-train' if n else 'blocked-preflight','run_id':run_id+'-localization','seed':split['seed'],'config':{'experiment':config['experiment'],'protocol':bind(protocol,root),'system':bind(run/'system.json',root),'source_snapshot':summary['config']['system_snapshot'],'scorer':bind(Path(__file__),root)},'sample_ids':[r['identity'] for r in observed],'metrics':metrics,'evidence':bind(out,root)})
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run_id');score(parser.parse_args().run_id)
