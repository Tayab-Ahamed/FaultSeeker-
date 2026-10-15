"""Build a self-contained candidate evidence bundle; do not invent annotations."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.evidence_manifest import audit_dataset, digest_file


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')


def rebuild_evidence(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    hunt = root / 'reports/provenance_hunt'
    legacy = root / 'reports/claim_closure/cohort'
    old = json.loads((legacy / 'records.json').read_text(encoding='utf-8'))
    extra = json.loads((hunt / 'new_candidates.json').read_text(encoding='utf-8'))['rows']
    pairs = {r['txn_hash']: r for r in json.loads((hunt / 'reviewed_source_pairs.json').read_text(encoding='utf-8'))}
    records, observations = [], []
    for ordinal, candidate in enumerate(old + extra, 1):
        is_new = ordinal > len(old)
        record = {'txn_hash': candidate['txn_hash'], 'chain': candidate['chain']} if is_new else dict(candidate)
        record['sources'] = []
        folder = output / 'artifacts' / f'row_{ordinal:04d}'

        def copy(path, name):
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            return str(target.relative_to(output)).replace('\\', '/')

        if not is_new:
            for name in ('ground_truth', 'transaction', 'receipt', 'trace', 'verification'):
                if candidate.get(name):
                    path = legacy / candidate[name]
                    record[name] = copy(path, path.name)
            for source in candidate.get('sources', []):
                record['sources'].append({**source, 'artifact': copy(legacy / source['artifact'], Path(source['artifact']).name)})
        else:
            source = candidate['index_artifact']
            record['sources'].append({'url': candidate['index_url'], 'publisher_id': 'SunWeb3Sec-DeFiHackLabs',
                'artifact': copy(root / source['file'], 'published_index.gz'), 'sha256': source['sha256']})
            record['membership_scope'] = 'New transaction-reference candidate; not an identified missing member of the original paper population'
        observed = {'ordinal': ordinal, 'txn_hash': record['txn_hash'], 'chain': record['chain'], 'new_candidate': is_new}
        acquisition = hunt / 'ethereum' / (record['txn_hash'] + '.json')
        if record['chain'] == 'eth' and acquisition.is_file():
            data = json.loads(acquisition.read_text(encoding='utf-8'))
            observed['single_provider_identity_receipt_match'] = data.get('identity_receipt_match', False)
            observed['single_provider_both_null'] = data.get('rpc_null_result', False)
            observed['live_identity_evidence'] = copy(acquisition, 'live_identity.json')
            # Preserve the byte-bound replay evidence for the two recorded
            # captures. Other receipts are identity evidence, not adjudication.
            if data.get('identity_receipt_match') and not record.get('transaction'):
                for name in ('transaction', 'receipt'):
                    target = folder / (name + '.json')
                    write(target, data[name]['result'])
                    record[name] = str(target.relative_to(output)).replace('\\', '/')
        if record['txn_hash'] in pairs:
            for source in pairs[record['txn_hash']]['sources']:
                original = root / source['artifact']
                if digest_file(original) != source['sha256']:
                    raise ValueError('Reviewed source digest mismatch')
                record['sources'].append({'url': source['url'], 'publisher_id': source['publisher'],
                    'artifact': copy(original, source['sha256'] + '.gz'), 'sha256': source['sha256']})
            observed['reviewed_primary_source_pair'] = True
        # No labels, function identities, attackers, reviewers, or chain
        # verification records are manufactured from incident references.
        records.append(record)
        observations.append(observed)
    write(output / 'records.json', records)
    report = audit_dataset(output / 'records.json', output, target=246)
    for decision, observed in zip(report['rows'], observations):
        decision.update(observed)
    report.update(original_rows=len(old), new_candidate_rows=len(extra),
        original_dataset_sha256=digest_file(root / 'reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv'),
        scope='246 candidate identities, zero implied paper-population membership or exploit-label adjudications')
    write(output / 'row_decisions.json', report)
    write(output / 'accepted_records.json', [r for r, d in zip(records, report['rows']) if d['accepted']])
    return report


if __name__ == '__main__':
    result = rebuild_evidence(ROOT, ROOT / 'reports/provenance_hunt/cohort')
    print(json.dumps({k: result[k] for k in ('input_rows', 'accepted_rows', 'original_rows', 'new_candidate_rows')}))
