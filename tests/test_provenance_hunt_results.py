def test_new_candidates_never_become_adjudicated_exploits_from_receipts(tmp_path):
    import json
    from pathlib import Path
    from scripts.summarize_provenance_hunt import rebuild_evidence
    root = Path(__file__).resolve().parents[1]
    result = rebuild_evidence(root, tmp_path)
    assert result['input_rows'] == 246
    assert result['accepted_rows'] == 0
    records = json.loads((tmp_path / 'records.json').read_text())
    assert all(not r.get('annotation') for r in records)
    assert all('reentrancy_label' not in r and not r.get('ground_truth') for r in records[231:])


def test_recorded_search_covers_every_original_exact_identity_once():
    import csv
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    with (root / 'reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv').open(encoding='utf-8-sig') as handle:
        originals = list(csv.DictReader(handle))
    queries = []
    for path in sorted((root / 'reports/provenance_hunt/search').glob('batch_*.json')):
        queries.extend(json.loads(path.read_text(encoding='utf-8'))['queries'])
    assert [(q['ordinal'], q['chain'], q['txn_hash']) for q in queries] == [
        (i, row['chain'], row['txn_hash']) for i, row in enumerate(originals, 1)]


def test_cached_http_sources_match_both_compressed_and_original_body_hashes():
    import gzip
    import hashlib
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for path in (root / 'reports/provenance_hunt/http').glob('*.json'):
        artifact = json.loads(path.read_text(encoding='utf-8'))
        if not artifact.get('file'):
            continue
        body = (root / artifact['file']).read_bytes()
        assert hashlib.sha256(body).hexdigest() == artifact['sha256']
        assert hashlib.sha256(gzip.decompress(body)).hexdigest() == artifact['body_sha256']
