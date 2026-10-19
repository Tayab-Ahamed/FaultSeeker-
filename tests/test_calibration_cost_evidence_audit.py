from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_calibration_cost_audit_blocks_empirical_claims_without_external_effects():
    from scripts.reproduce.audit_calibration_cost_evidence import audit

    report = audit(ROOT)
    assert report['external_effects'] is False
    assert report['status'] == 'BLOCKED_EMPIRICAL_EVIDENCE'
    assert report['calibration']['feature_names_match'] is True
    assert report['calibration']['deployable_production_schema'] is False
    assert report['calibration']['in_sample_counts_consistent'] is True
    assert report['calibration']['cv_counts_consistent'] is True
    assert report['cost']['completed_n'] == 0
    assert report['cost']['measured_saving_fraction'] is None
    assert report['cost']['modeled_cost_reduction_pct'] == 35.0
    assert report['cost']['empty_tracker_measured'] is False


def test_calibration_cost_audit_does_not_require_provider_credentials():
    from scripts.reproduce.audit_calibration_cost_evidence import audit

    report = audit(ROOT)
    assert report['cost']['provider_calls'] == 0
    assert report['cost']['measured_usage_log_present'] is False
