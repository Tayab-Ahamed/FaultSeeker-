import shutil
from pathlib import Path

from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator
from faultseeker.research.cost_tracker import CostTracker
from scripts.reproduce.audit_calibration_cost_evidence import audit_calibration, classify_cost_report


ROOT = Path(__file__).resolve().parents[1]


def test_calibration_cost_audit_blocks_empirical_claims_without_external_effects():
    from scripts.reproduce.audit_calibration_cost_evidence import audit

    report = audit(ROOT)
    assert report['external_effects'] is False
    assert report['status'] == 'BLOCKED_EMPIRICAL_EVIDENCE'
    assert report['calibration']['feature_names_match'] is True
    assert report['calibration']['deployable_production_schema'] is False
    assert report['calibration']['model_integrity'] is True
    assert report['calibration']['provenance']['valid'] is False
    assert report['calibration']['in_sample_counts_consistent'] is True
    assert report['calibration']['cv_counts_consistent'] is True
    assert report['calibration']['in_sample_metric_scope'] == 'in-sample_same_rows'
    assert report['calibration']['cv_has_ece'] is False
    assert report['calibration']['cv_artifact_complete'] is False
    assert report['calibration']['metrics_regenerable_from_retained_inputs'] is False
    assert report['cost']['completed_n'] == 0
    assert report['cost']['measured_saving_fraction'] is None
    assert report['cost']['modeled_cost_reduction_pct'] == 35.0
    assert report['cost']['state_report_consistent'] is True
    assert report['cost']['selection_manifest_present'] is False
    assert report['cost']['modeled_arithmetic_consistent'] is True
    assert report['cost']['empty_tracker_measured'] is True
    assert report['cost']['empty_tracker_qualifies_as_empirical_evidence'] is False


def test_calibration_cost_audit_does_not_require_provider_credentials():
    from scripts.reproduce.audit_calibration_cost_evidence import audit

    report = audit(ROOT)
    assert report['cost']['provider_calls'] == 0
    assert report['cost']['measured_usage_log_present'] is False


def test_legacy_fixture_is_reported_without_mutating_inspected_artifacts(tmp_path):
    fixture_models = tmp_path / 'data/models'
    fixture_models.mkdir(parents=True)
    source = ROOT / 'data/models'
    for name in ('calibrator_metrics.json', 'calibrator_cv_metrics.json'):
        shutil.copyfile(source / name, fixture_models / name)
    model = LogisticConfidenceCalibrator()
    model.fit([{name: 0.1 for name in FEATURE_NAMES},
               {name: 0.9 for name in FEATURE_NAMES}], [0, 1], epochs=2)
    model.save(str(fixture_models / 'calibrator.json'))
    before = {path.name: path.read_bytes() for path in fixture_models.iterdir()}

    report = audit_calibration(tmp_path)

    assert report['status'] == 'BLOCKED_NON_DEPLOYABLE'
    assert report['provenance']['present'] is False
    assert {path.name: path.read_bytes() for path in fixture_models.iterdir()} == before


def test_cost_report_distinguishes_observed_usage_from_modeled_counterfactual():
    empty = CostTracker().report()
    empty_semantics = classify_cost_report(empty)
    assert empty_semantics['observed_runtime_usage'] is False
    assert empty_semantics['empirical_measurement_eligible'] is False

    tracker = CostTracker()
    tracker.record_transaction()
    tracker.record_llm_call('stage2', 'cloud', 'gpt-4o', 100, 20)
    observed = tracker.report()
    observed_semantics = classify_cost_report(observed)
    assert observed_semantics['observed_runtime_usage'] is True
    assert observed_semantics['calculated_cost_from_observed_usage'] is True
    assert observed_semantics['empirical_measurement_eligible'] is True
    assert observed_semantics['verified_invoice_cost_present'] is False
