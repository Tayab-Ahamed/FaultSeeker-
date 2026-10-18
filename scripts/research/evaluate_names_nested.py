"""Nested four-inner/five-outer selection over the frozen B4 search space."""
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.research import evaluate_names_semantics_extended as learner
base = learner.base
OUT = learner.OUT
CONFIGS = list(itertools.product(('unigram', 'bigram', 'char'), (1.,10.,100.), (1.,3.)))


def select(rows, folds, outer):
    summaries = []
    for mode, c, scale in CONFIGS:
        learner.MODE = mode
        ranks = []
        for inner in range(5):
            if inner == outer:
                continue
            train = [i for i in range(len(rows)) if folds[i] not in (outer, inner)]
            validation = [i for i in range(len(rows)) if folds[i] == inner]
            model = learner.fit(rows, train, c, scale)
            ranks.extend(base.first_hit(learner.predict(model, rows[i], scale), rows[i]['targets']) for i in validation)
        summaries.append({'config': [mode,c,scale], 'inner_selection_hits': base.hit_counts(ranks)})
    chosen = max(summaries, key=lambda r: tuple(r['inner_selection_hits']))
    return chosen['config'], summaries


def main():
    base.install_offline_guard()
    destination = OUT / 'nested_results.json'
    if destination.exists():
        raise RuntimeError('Refusing overwrite')
    rows, hashes = base.read_rows()
    manifest = json.loads(base.MANIFEST.read_text(encoding='utf-8'))
    sources = sorted([r for r in manifest['rows'] if r.get('status') == 'ok'], key=lambda r:(r['txn_hash'],r['filename']))
    for row, source in zip(rows,sources):
        row['docs'] = learner.documents([e['address'] for e in row['evidence']], source.get('predictions') or [],
                                         str((source.get('cast') or {}).get('output_tail') or ''))
        row['numeric'] = [[e[k] for k in learner.NUMERIC]+[1/(j+1)] for j,e in enumerate(row['evidence'])]
    groups = base.connected_groups(rows)
    folds = base.assign_folds(groups)
    for group in groups:
        for i in group:
            rows[i]['group_size'] = len(group)
    predictions, audits = [None]*len(rows), []
    for outer in range(5):
        chosen, summaries = select(rows, folds, outer)
        learner.MODE, c, scale = chosen
        train = [i for i in range(len(rows)) if folds[i] != outer]
        test = [i for i in range(len(rows)) if folds[i] == outer]
        model = learner.fit(rows, train, c, scale)
        for i in test:
            predictions[i] = learner.predict(model, rows[i], scale)
        audits.append({'outer':outer,'train':train,'test':test,'selected':chosen,'inner_selection_diagnostics':summaries})
        print('outer',outer,'selected',chosen,flush=True)
    ranks = [base.first_hit(p,r['targets']) for p,r in zip(predictions,rows)]
    baseline = [base.first_hit([e['address'] for e in r['evidence']],r['targets']) for r in rows]
    unique, seen = [],set()
    for i,row in enumerate(rows):
        if row['tx'] not in seen:
            seen.add(row['tx']); unique.append(i)
    for relative in ('scripts/research/evaluate_names_nested.py','scripts/research/evaluate_names_semantics_extended.py',
                     'scripts/research/names_semantics_corrected.py','scripts/research/names_semantics.py',
                     'scripts/research/address_ranking_phase1.py','faultseeker/function_analysis/function_ranker.py',
                     'faultseeker/function_analysis/candidate_generation.py','reports/localization_continuous/names_semantics_extended/NESTED_PROTOCOL.md'):
        hashes[ROOT/relative] = base.sha(ROOT/relative)
    assert all(base.sha(p)==h for p,h in hashes.items())
    result = {'research_validation':True,'prior_research_outcomes_seen':True,'hits':base.hit_counts(ranks),
              'baseline_hits':base.hit_counts(baseline),'unique109_hits':base.hit_counts([ranks[i] for i in unique]),
              'metrics':base.metrics(ranks),'audits':audits,'oof_ranks':ranks,'oof_rankings':predictions,
              'input_sha256':{p.relative_to(ROOT).as_posix():h for p,h in hashes.items()},'network_calls':0,'fresh_batches_read':0}
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('nested OOF',result['hits'],'unique109',result['unique109_hits'])


if __name__=='__main__':
    main()
