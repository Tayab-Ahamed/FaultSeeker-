import json


def _write_bound_fixture(tmp_path, ordinal=1):
    from benchmark.research_protocol import bind, write_json

    tx_hash = '0x' + format(ordinal, '064x')
    block_hash = '0x' + 'b' * 64
    rpc = tmp_path / 'rpc.json'
    write_json(rpc, {
        'mode': 'live-rpc', 'txn_hash': tx_hash, 'chain': 'eth', 'chain_id': 1,
        'transaction': {'hash': tx_hash, 'chainId': '0x1', 'blockHash': block_hash},
        'receipt': {'transactionHash': tx_hash, 'blockHash': block_hash, 'status': '0x1'},
    })
    sources = []
    observations = []
    for index, text in enumerate((
            'The callback permits reentrancy before the account balance is updated.',
            'An external receiver reenters the withdrawal before its balance update.')):
        source = tmp_path / f'source-{index}.txt'
        source.write_text(text, encoding='utf-8')
        binding = bind(source, tmp_path)
        publisher = f'publisher-{index}'
        sources.append({
            'publisher_id': publisher,
            'independence_group': publisher,
            'artifact': binding,
            'review_status': 'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED',
            'independence_basis': 'Independent fixture publishers',
            'identity_basis': tx_hash,
        })
        observations.append({
            'publisher_id': publisher,
            'source_artifact': binding,
            'vulnerability_class': 'Reentrancy',
            'mechanism_excerpt': text,
        })
    annotation_path = tmp_path / 'annotation.json'
    write_json(annotation_path, {
        'mode': 'public-source-consensus-v1',
        'adjudication_author': 'Codex',
        'txn_hash': tx_hash,
        'chain': 'eth',
        'is_exploit': True,
        'vuln_type': 'Reentrancy',
        'uncategorized': False,
        'independent_observations': observations,
        'adjudication_basis': 'Both fixture publishers agree',
    })
    return {
        'txn_hash': tx_hash,
        'chain': 'eth',
        'sources': sources,
        'rpc': bind(rpc, tmp_path),
        'annotation_record': bind(annotation_path, tmp_path),
    }


def _manifest(tmp_path, records, target=None):
    return {
        'schema': 2,
        'target_count': len(records) if target is None else target,
        'accepted_count': len(records),
        'remaining_to_target': max(0, (len(records) if target is None else target) - len(records)),
        'chains': {'eth': len(records)},
        'not_independent_human_review': True,
        'records': records,
    }


def _write_manifest(tmp_path, value):
    path = tmp_path / 'benchmark' / 'cohort_manifest.json'
    path.parent.mkdir()
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def test_bound_manifest_acceptance_and_accounting_are_checked(tmp_path):
    from benchmark.validate_cohort_manifest import audit_manifest

    row = _write_bound_fixture(tmp_path)
    result = audit_manifest(_write_manifest(tmp_path, _manifest(tmp_path, [row])), tmp_path, target=1)
    assert result['manifest_valid'] is True
    assert result['status'] == 'READY-FOR-EXPERIMENT'
    assert result['accepted_rows'] == 1
    assert result['pending_rows'] == result['excluded_rows'] == 0


def test_missing_bound_evidence_is_pending_not_accepted_or_excluded(tmp_path):
    from benchmark.validate_cohort_manifest import audit_manifest

    row = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth'}
    result = audit_manifest(_write_manifest(tmp_path, _manifest(tmp_path, [row])), tmp_path, target=1)
    assert result['manifest_valid'] is False
    assert result['status'] == 'BLOCKED-BY-DATA'
    assert result['pending_rows'] == 1
    assert result['excluded_rows'] == 0
    assert result['rows'][0]['status'] == 'pending'


def test_invalid_identity_and_duplicate_identity_are_excluded(tmp_path):
    from benchmark.validate_cohort_manifest import audit_manifest

    row = {'txn_hash': 'not-a-hash', 'chain': 'eth'}
    duplicate = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth'}
    result = audit_manifest(
        _write_manifest(tmp_path, _manifest(tmp_path, [duplicate, dict(duplicate)])),
        tmp_path, target=2)
    assert result['manifest_valid'] is False
    assert result['excluded_rows'] == 2
    assert all(item['status'] == 'excluded' for item in result['rows'])

    invalid_dir = tmp_path / 'invalid'
    invalid_dir.mkdir()
    invalid = audit_manifest(_write_manifest(invalid_dir, _manifest(invalid_dir, [row])),
                             invalid_dir, target=1)
    assert invalid['rows'][0]['status'] == 'excluded'


def test_manifest_count_and_chain_accounting_mismatch_is_reported(tmp_path):
    from benchmark.validate_cohort_manifest import audit_manifest

    row = {'txn_hash': '0x' + 'a' * 64, 'chain': 'eth'}
    manifest = _manifest(tmp_path, [row], target=2)
    manifest['accepted_count'] = 2
    manifest['chains'] = {'bsc': 1}
    result = audit_manifest(_write_manifest(tmp_path, manifest), tmp_path, target=2)
    assert 'MANIFEST_ACCEPTED_COUNT_MISMATCH' in result['manifest_reasons']
    assert 'MANIFEST_CHAIN_COUNTS_MISMATCH' in result['manifest_reasons']
    assert 'PUBLISHED_RECORD_NOT_ACCEPTED' in result['manifest_reasons']
