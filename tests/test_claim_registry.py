import json
import pytest
from benchmark.claim_registry import CLAIMS, claim_report
from benchmark.build_paper_benchmark import freeze_cohort


def test_registry_accounts_for_all_31_claims_without_promoting_fixture_proof():
    assert [r['id'] for r in CLAIMS] == list(range(1, 32))
    report = claim_report({}, {'accepted_rows': 0, 'additional_verified_rows_needed': 246})
    assert len(report['claims']) == 31
    assert all(r['status'] != 'VERIFIED' for r in report['claims'])
    assert next(r for r in report['claims'] if r['id'] == 3)['status'] == 'BLOCKED-BY-DATA'


def test_local_status_requires_every_bound_test_to_pass():
    claim = next(r for r in CLAIMS if r['id'] == 23)
    passed = {node: 'passed' for node in claim['tests']}
    report = claim_report(passed, {'accepted_rows': 0})
    assert next(r for r in report['claims'] if r['id'] == 23)['local_proof'] == 'PASSED'
    passed[claim['tests'][0]] = 'failed'
    report = claim_report(passed, {'accepted_rows': 0})
    assert next(r for r in report['claims'] if r['id'] == 23)['local_proof'] == 'FAILED-OR-MISSING'


def test_cohort_builder_refuses_to_pad_or_emit_partial_dataset(tmp_path):
    source = tmp_path/'input.json'
    source.write_text(json.dumps([{'txn_hash': '0x'+'a'*64, 'chain': 'eth'}]))
    output = tmp_path/'cohort.json'
    with pytest.raises(ValueError, match='BLOCKED-BY-DATA'):
        freeze_cohort(source, output, target=246)
    assert not output.exists()


def test_tools_claim_requires_executed_compiled_integration_tests():
    claim = next(row for row in CLAIMS if row['id'] == 26)
    outcomes = {node: 'passed' for node in claim['tests']}
    report = claim_report(outcomes, {'accepted_rows': 0})
    assert next(row for row in report['claims'] if row['id'] == 26)['status'] == 'VERIFIED-COMPILED-EVM'
    compiled = [node for node in claim['tests'] if 'test_compiled_evm_integration' in node]
    assert len(compiled) >= 3
    outcomes[compiled[0]] = 'skipped'
    report = claim_report(outcomes, {'accepted_rows': 0})
    assert next(row for row in report['claims'] if row['id'] == 26)['status'] == 'PENDING-CREDENTIALS'
