"""Fixed outer-fold-only lexical experiments on original110."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.research import address_ranking_phase1 as base
from scripts.research.names_semantics_corrected import documents, NUMERIC
OUT = ROOT / 'reports/localization_continuous/names_semantics_corrected'


def training(rows, indices):
    docs, numeric, labels, weights = [], [], [], []
    for i in indices:
        row = rows[i]
        docs.extend(row['docs']); numeric.extend(row['numeric'])
        labels.extend(int(e['address'] in row['targets']) for e in row['evidence'])
        weights.extend([1 / len(row['evidence'])] * len(row['evidence']))
    return docs, np.asarray(numeric), np.asarray(labels), np.asarray(weights)


def fit(rows, indices, c, scale):
    docs, numeric, labels, weights = training(rows, indices)
    vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b[a-z]{2,}\b')
    # No manufactured placeholder token if every training document is empty.
    lexical = vectorizer.fit_transform(docs) if any(docs) else csr_matrix((len(docs), 0))
    scaler = StandardScaler().fit(numeric)
    matrix = hstack([csr_matrix(scaler.transform(numeric)), lexical * scale]).tocsr()
    model = LogisticRegression(C=c, max_iter=2000, random_state=base.SEED)
    model.fit(matrix, labels, sample_weight=weights)
    return model, scaler, vectorizer if any(docs) else None


def predict(bundle, row, scale):
    if not row['evidence']:
        return []
    model, scaler, vectorizer = bundle
    lexical = vectorizer.transform(row['docs']) if vectorizer else csr_matrix((len(row['docs']), 0))
    x = hstack([csr_matrix(scaler.transform(row['numeric'])), lexical * scale]).tocsr()
    scores = model.predict_proba(x)[:, 1]
    return [row['evidence'][i]['address'] for i in sorted(range(len(scores)), key=lambda i: (-scores[i], i))]


def main():
    import copy
    base.install_offline_guard()
    destination = OUT / 'results.json'
    if destination.exists():
        raise RuntimeError('Refusing to overwrite experiment')
    rows, hashes = base.read_rows()
    manifest = json.loads(base.MANIFEST.read_text(encoding='utf-8'))
    sources = sorted([r for r in manifest['rows'] if r.get('status') == 'ok'], key=lambda r: (r['txn_hash'], r['filename']))
    for row, source in zip(rows, sources):
        row['docs'] = documents([e['address'] for e in row['evidence']], source.get('predictions') or [],
                                str((source.get('cast') or {}).get('output_tail') or ''))
        row['numeric'] = [[e[k] for k in NUMERIC] + [1 / (j + 1)] for j, e in enumerate(row['evidence'])]
    folds = base.assign_folds(base.connected_groups(rows))
    baseline = [base.first_hit([e['address'] for e in r['evidence']], r['targets']) for r in rows]
    assert base.hit_counts(baseline) == [55, 68, 76]
    unique, seen = [], set()
    for i, row in enumerate(rows):
        if row['tx'] not in seen:
            unique.append(i); seen.add(row['tx'])
    report = {'exploratory': True, 'baseline_hits': base.hit_counts(baseline), 'folds': folds, 'variants': {},
              'nonempty_candidate_documents': sum(bool(d) for r in rows for d in r['docs']),
              'candidate_documents': sum(len(r['docs']) for r in rows), 'network_calls': 0, 'fresh_batches_read': 0}
    for c in (.1, 1., 10.):
        for scale in (.3, 1., 3.):
            predictions = [None] * len(rows); audits = []
            for fold in range(5):
                train = [i for i in range(len(rows)) if folds[i] != fold]
                test = [i for i in range(len(rows)) if folds[i] == fold]
                bundle = fit(rows, train, c, scale)
                for i in test:
                    predictions[i] = predict(bundle, rows[i], scale)
                poisoned = copy.deepcopy(rows)
                for i in test:
                    poisoned[i]['targets'] = ['heldout-label-poison']
                    poisoned[i]['docs'] = ['heldoutuniquetoken'] * len(poisoned[i]['docs'])
                alternate = fit(poisoned, train, c, scale)
                assert np.array_equal(bundle[0].coef_, alternate[0].coef_)
                assert bundle[2].vocabulary_ == alternate[2].vocabulary_
                assert 'heldoutuniquetoken' not in bundle[2].vocabulary_
                audits.append({'fold': fold, 'train': train, 'test': test, 'vocabulary_size': len(bundle[2].vocabulary_),
                               'heldout_label_and_text_fit_independence': True})
            ranks = [base.first_hit(p, r['targets']) for p, r in zip(predictions, rows)]
            hits = base.hit_counts(ranks)
            name = f'C{c}_lexical{scale}'
            report['variants'][name] = {'hits': hits, 'delta_hits': [x-y for x,y in zip(hits, base.hit_counts(baseline))],
                'metrics': base.metrics(ranks), 'unique109_hits': base.hit_counts([ranks[i] for i in unique]),
                'oof_ranks': ranks, 'oof_rankings': predictions, 'audits': audits}
            print(name, hits, flush=True)
    for relative in ('scripts/research/evaluate_names_semantics_corrected.py', 'scripts/research/names_semantics_corrected.py', 'scripts/research/names_semantics.py',
                     'scripts/research/address_ranking_phase1.py', 'faultseeker/function_analysis/function_ranker.py',
                     'faultseeker/function_analysis/candidate_generation.py', 'reports/localization_continuous/names_semantics_corrected/PROTOCOL.md'):
        hashes[ROOT / relative] = base.sha(ROOT / relative)
    assert all(base.sha(p) == digest for p, digest in hashes.items())
    report['input_sha256'] = {p.relative_to(ROOT).as_posix(): digest for p,digest in hashes.items()}
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
