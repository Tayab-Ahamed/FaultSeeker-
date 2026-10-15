import csv
import json


def test_rebuild_retains_every_row_without_inventing_annotation(tmp_path):
    from scripts.rebuild_claim_cohort import rebuild
    source = tmp_path/'rows.csv'
    rows = [{'txn_hash':'0x'+'ab'*32,'chain':'eth','analysis':'["https://example.org/report"]'},
            {'txn_hash':'0x'+'cd'*32,'chain':'bsc','analysis':'[]'}]
    with source.open('w',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
    gt = tmp_path/'gt';gt.mkdir()
    (gt/(rows[0]['txn_hash']+'.json')).write_text(json.dumps({
        'transaction_hash':[rows[0]['txn_hash']], 'cause':'legacy label', 'location':{'x':['y']}}))
    report = rebuild(source,gt,tmp_path/'evidence')
    assert report['input_rows'] == 2
    assert report['accepted_rows'] == 0
    assert len(report['rows']) == 2
    assert all('missing_independent_annotation' in row['missing'] for row in report['rows'])
    assert report['rows'][0]['legacy_gt_found'] is True


def test_rebuild_preserves_filename_payload_identity_conflict(tmp_path):
    from scripts.rebuild_claim_cohort import inventory_ground_truth
    filename_hash = '0x'+'ab'*32
    (tmp_path/(filename_hash+'.json')).write_text(json.dumps({'transaction_hash':['0x'+'cd'*32]}))
    inventory = inventory_ground_truth(tmp_path)
    assert inventory[0]['filename_identity_matches_payload'] is False


def test_provenance_reader_supports_real_compressed_trace_artifacts(tmp_path):
    import gzip
    from benchmark.evidence_manifest import validate_record
    tx = '0x'+'ab'*32
    with gzip.open(tmp_path/'trace.json.gz','wt',encoding='utf-8') as handle:
        json.dump({'transaction_hash':tx,'chain':'eth','complete':True,
                   'raw_trace':{'call':{'type':'CALL'}},'tracer_config':{'call':'callTracer'},
                   'capture_version':'test-format'},handle)
    result = validate_record({'txn_hash':tx,'chain':'eth','trace':'trace.json.gz'},tmp_path)
    assert 'invalid_trace_json' not in result['missing']
    assert 'missing_trace' not in result['missing']


def test_rebuilt_cohort_accounts_for_every_source_row_and_revalidates_gaps():
    from pathlib import Path
    from benchmark.evidence_manifest import validate_record
    root=Path(__file__).resolve().parents[1]
    with (root/'benchmark/benchmark_classification_fixed.csv').open(encoding='utf-8-sig') as handle:
        original=list(csv.DictReader(handle))
    directory=root/'reports/claim_closure/cohort'
    rebuilt=json.loads((directory/'records.json').read_text())
    decisions=json.loads((directory/'row_decisions.json').read_text())
    assert [(r['chain'],r['txn_hash']) for r in rebuilt] == [(r['chain'],r['txn_hash']) for r in original]
    assert len(decisions['rows'])==len(original)
    for record,decision in zip(rebuilt,decisions['rows']):
        result=validate_record(record,directory)
        assert result['accepted']==decision['accepted']
        assert set(result['missing'])==set(decision['missing'])
        assert record.get('annotation') is None


def test_captured_rows_remain_rejected_without_independent_attestations():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'reports/claim_closure/cohort'
    report=json.loads((root/'row_decisions.json').read_text())
    captured=[r for r in report['rows'] if r.get('on_chain_capture')]
    assert len(captured)==2
    for row in captured:
        assert not row['accepted']
        assert 'missing_trace' not in row['missing']
        assert 'missing_independent_annotation' in row['missing']
        assert 'missing_independent_rpc_confirmation' in row['missing']
