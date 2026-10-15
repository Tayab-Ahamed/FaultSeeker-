"""History evidence must not silently become empirical verification."""
import pytest
import hashlib
import json
from pathlib import Path

from scripts.collect_canonical_evidence import csv_inventory, metric_scope, original_partition


def test_csv_inventory_counts_rows_separately_from_unique_hashes():
    raw = b'tx_hash,chain,vuln_type\n0xa,Ethereum,reentrancy\n0xa,Ethereum,logic\n0xb,BSC,access\n'
    result = csv_inventory(raw)
    assert result['rows'] == 3
    assert result['unique_hashes'] == 2
    assert result['chains'] == ['BSC', 'Ethereum']
    assert result['reentrancy_labeled'] == 1
    from scripts.finalize_canonical_review import call_count_bin
    assert call_count_bin({'functioncall_count': ''}) is None
    assert call_count_bin({'functioncall_count': 'nan'}) is None
    assert call_count_bin({'functioncall_count': '-1'}) is None
    assert call_count_bin({'functioncall_count': '5'}) == 'Simple'
    assert call_count_bin({'functioncall_count': '6'}) == 'Moderate'
    assert call_count_bin({'functioncall_count': '501'}) == 'Exceptionally Complex'


def test_reconstructions_never_enter_original_ground_truth_set():
    result = original_partition({'a.json', 'b.json'}, {'a.json', 'b.json', 'c.json'})
    assert result == {'original': ['a.json', 'b.json'], 'reconstruction': ['c.json']}
    with pytest.raises(ValueError):
        original_partition({'missing.json'}, {'a.json'})


def test_modeled_cost_and_absent_predictions_cannot_be_empirical():
    assert metric_scope('runtime_cost.json') == 'MODELED-NOT-MEASURED'
    assert metric_scope('reentrancy_metrics.json') == 'NO-EVALUATED-PREDICTIONS'
    assert metric_scope('honest_research_tables.tex') == 'RECORDED-TABLE-REQUIRES-RUN-LINEAGE'
    assert metric_scope('localization_metrics.json') == 'RECORDED-AGGREGATE-REQUIRES-RAW-PREDICTIONS'


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/canonical_history'


def test_every_registered_canonical_blob_matches_git_identity_and_sha256():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    assert manifest['shallow'] == 'false'
    assert len(manifest['reachable_commits']) == 53
    for artifact in manifest['artifacts']:
        path = (ROOT / artifact['cache']).resolve()
        assert path.is_relative_to(BASE.resolve())
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == artifact['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == artifact['git_blob_sha1']


def test_history_counts_do_not_repeat_incorrect_no_246_premise():
    history = json.loads((BASE / 'cohort_history.json').read_text())
    assert history['has_246_row_version']
    early = next(v for v in history['versions'].values() if v['rows'] == 246)
    assert early['unique_hashes'] == 246
    assert early['physical_data_lines'] == 248
    assert early['blank_lines'] == 2
    assert early['malformed_evm_hashes'] == 15
    assert history['ground_truth_counts'] == {'original': 115, 'reconstruction': 48}
    assert history['original_ground_truth_audit']['unique_transaction_hashes'] == 114
    frozen = history['requested_231_snapshot']
    assert frozen['rows'] == 231 and frozen['reentrancy_labeled'] == 17
    assert len(frozen['chains']) == 8
    assert all('2026-04-03' in x['first_add'] for x in history['ground_truth_origins'] if x['kind'] == 'original')


def test_paper_map_distinguishes_recorded_reproduced_modeled_and_unsupported_numbers():
    mapping = json.loads((BASE / 'paper_vs_repo.json').read_text())
    rows = {r['key']: r for r in mapping['numbers']}
    assert rows['overall_saving']['replacement'] == '35% modeled; measured savings unavailable'
    assert rows['guidance']['verdict'] == 'UNSUPPORTED'
    assert rows['historical_f1']['verdict'] == 'REPRODUCED-FEATURE-HARNESS'
    assert rows['localization']['verdict'] == 'RECORDED-NOT-REPRODUCED'
    assert rows['detector_f1']['replacement'] == 'Undefined: canonical recompute evaluated 0 transactions'
    assert len(mapping['reopened_decisions']) == 18
    assert all(d['status'] == 'UNVERIFIABLE' and d['reason'] and d['missing_input']
               for d in mapping['reopened_decisions'])
