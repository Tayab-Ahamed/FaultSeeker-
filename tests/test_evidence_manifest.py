import csv
import json
from pathlib import Path

from benchmark.evidence_manifest import audit_dataset, validate_record, digest_file


def test_unknown_provenance_never_becomes_verified(tmp_path):
    record = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth', 'pool_status': 'verified_benchmark'}
    result = validate_record(record, tmp_path)
    assert not result['accepted']
    assert 'missing_transaction' in result['missing']
    assert 'missing_receipt' in result['missing']
    assert 'missing_trace' in result['missing']
    assert 'missing_independent_sources' in result['missing']


def test_reviewer_string_is_not_counted_as_multiple_independent_reviewers(tmp_path):
    record = {'txn_hash':'0x'+'a'*64,'chain':'eth','annotation':{
        'reviewers':'alice,bob','adjudicated_label':'reentrancy','attacker_addresses':['0xattacker']}}
    assert 'missing_independent_annotation' in validate_record(record,tmp_path)['missing']


def test_ground_truth_identity_mismatch_is_rejected(tmp_path):
    gt = tmp_path / 'gt.json'
    gt.write_text(json.dumps({'transaction_hash': ['0x' + 'b' * 64]}))
    record = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth', 'ground_truth': 'gt.json'}
    assert 'ground_truth_identity_mismatch' in validate_record(record, tmp_path)['missing']


def test_all_rows_are_audited_and_pending_rows_are_not_padded(tmp_path):
    path = tmp_path / 'rows.csv'
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['txn_hash', 'chain', 'vuln_type'])
        writer.writeheader()
        writer.writerows([{'txn_hash': '0x' + 'a' * 64, 'chain': 'eth', 'vuln_type': 'Reentrancy'},
                         {'txn_hash': 'malformed', 'chain': 'bsc', 'vuln_type': 'Access Control'}])
    result = audit_dataset(path, evidence_root=tmp_path, target=246)
    assert result['input_rows'] == 2
    assert len(result['rows']) == 2
    assert result['accepted_rows'] == 0
    assert result['additional_verified_rows_needed'] == 246
    assert result['status'] == 'BLOCKED-BY-DATA'
    assert 'invalid_transaction_hash' in result['rows'][1]['missing']


def test_artifact_paths_cannot_escape_evidence_root(tmp_path):
    record = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth', 'trace': '../outside.json'}
    assert 'unsafe_trace_path' in validate_record(record, tmp_path)['missing']


def test_digest_is_of_content_not_filename(tmp_path):
    first, second = tmp_path / 'one', tmp_path / 'two'
    first.write_bytes(b'original')
    second.write_bytes(b'original')
    assert digest_file(first) == digest_file(second)
    second.write_bytes(b'changed')
    assert digest_file(first) != digest_file(second)


def test_complete_artifact_manifest_accepts_then_detects_tampering(tmp_path):
    tx_hash, block_hash = '0x'+'a'*64, '0x'+'b'*64
    artifacts = {
        'transaction': {'hash': tx_hash, 'chainId': '0x1', 'blockHash': block_hash},
        'receipt': {'transactionHash': tx_hash, 'blockHash': block_hash, 'blockNumber': '0x123'},
        'trace': {'transaction_hash': tx_hash, 'chain': 'eth', 'complete': True,
                  'raw_trace': {'type': 'CALL'}, 'capture_version': 'test-fixture',
                  'tracer_config': {'tracer': 'callTracer'}},
        'ground_truth': {'transaction_hash': [tx_hash], 'cause': 'reentrancy', 'location': ['withdraw()']},
    }
    record = {'txn_hash': tx_hash, 'chain': 'eth', 'sources': [],
              'annotation': {'reviewers': ['reviewer-a', 'reviewer-b'],
                             'adjudicated_label': 'reentrancy', 'attacker_addresses': ['0xattacker']}}
    for name, payload in artifacts.items():
        path = tmp_path/(name+'.json')
        path.write_text(json.dumps(payload))
        record[name] = path.name
    for index in range(2):
        path = tmp_path/f'source{index}.txt'
        path.write_text(f'Independent source fixture {index}')
        record['sources'].append({'publisher_id': f'publisher{index}', 'url': f'https://source{index}.example/report',
                                  'artifact': path.name, 'sha256': digest_file(path)})
    verification = {'mode': 'live-rpc-and-replay', 'chain_id': 1,
                    'rpc_endpoints': ['provider-a', 'provider-b'], 'canonical_block_hash': block_hash,
                    'verified_at': '2026-10-14', 'tool_versions': {'capture': 'test-fixture'}}
    for name in ('transaction', 'receipt', 'trace'):
        verification[name+'_sha256'] = digest_file(tmp_path/record[name])
    (tmp_path/'verification.json').write_text(json.dumps(verification))
    record['verification'] = 'verification.json'
    assert validate_record(record, tmp_path)['accepted'] is True
    (tmp_path/'trace.json').write_text(json.dumps(dict(artifacts['trace'], raw_trace={'tampered': True})))
    assert 'trace_digest_mismatch' in validate_record(record, tmp_path)['missing']
