from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_claim_ledger_covers_all_registry_claims_with_allowed_statuses():
    from benchmark.claim_registry import CLAIMS
    from scripts.reproduce.claim_closure_ledger import STATUSES, build_ledger

    ledger = build_ledger(ROOT)
    assert [row['id'] for row in ledger['claims']] == [claim['id'] for claim in CLAIMS]
    assert all(row['status'] in STATUSES for row in ledger['claims'])
    assert sum(ledger['claim_counts'].values()) == len(CLAIMS)
    assert ledger['external_effects'] is False


def test_claim_ledger_preserves_current_cohort_and_frozen_batch_e():
    from scripts.reproduce.claim_closure_ledger import build_ledger

    ledger = build_ledger(ROOT)
    assert ledger['current_cohort']['target_count'] == 246
    assert ledger['current_cohort']['accepted_count'] == 14
    assert ledger['current_cohort']['remaining_to_target'] == 232
    versions = {row['manifest']: row for row in ledger['versioned_cohorts']}
    assert versions['benchmark/versions/cohort_v3_20261016/cohort_manifest.json']['accepted_rows'] == 20
    assert versions['benchmark/versions/cohort_v4_20261016/cohort_manifest.json']['accepted_rows'] == 22
    assert versions['benchmark/versions/cohort_v4_20261016/cohort_manifest.json']['status'] == 'BLOCKED-BY-DATA'
    assert ledger['frozen_batch_e']['n'] == 40
    assert ledger['frozen_batch_e']['recall_at_1'] == 0.35
    assert ledger['frozen_batch_e']['recall_at_3'] == 0.675
    assert ledger['frozen_batch_e']['recall_at_5'] == 0.825


def test_claim_ledger_does_not_promote_known_cost_or_calibration_gaps():
    from scripts.reproduce.claim_closure_ledger import build_ledger

    rows = {row['id']: row for row in build_ledger(ROOT)['claims']}
    assert rows[1]['status'] == 'EXTERNALLY_BLOCKED'
    assert rows[2]['status'] == 'UNVERIFIED'
    assert rows[2]['verification_result']['current_checkpoint_status'] == 'NOT_RUN_FULL_SUITE'
    assert rows[18]['status'] == 'CONTRADICTED_BY_CURRENT_EVIDENCE'
    assert rows[23]['status'] == 'VERIFIED_IMPLEMENTATION'
    assert rows[18]['missing_prerequisites']
    assert rows[23]['verification_result']['verification_scope']
