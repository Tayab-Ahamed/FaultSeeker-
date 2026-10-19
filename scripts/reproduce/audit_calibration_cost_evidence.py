"""Audit retained calibration and cost evidence without external effects.

This command reads committed/local artifacts only.  It does not load dotenv,
contact providers, train a model, write reports, or alter research batches.
Passing local integrity checks deliberately does not promote blocked empirical
claims to reproduced results.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator
from faultseeker.research.cost_tracker import CostTracker


def _read(root: Path, relative: str):
    path = root / relative
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _confusion_consistent(metrics, exploit_rows, benign_rows):
    return (
        metrics.get('tp', -1) + metrics.get('fn', -1) == exploit_rows
        and metrics.get('fp', -1) + metrics.get('tn', -1) == benign_rows
        and metrics.get('n', exploit_rows + benign_rows) == exploit_rows + benign_rows
    )


def _model_integrity(model):
    values = (model.weights, model.means, model.scales, [model.bias])
    return (
        model.feature_names == FEATURE_NAMES
        and all(len(row) == len(FEATURE_NAMES) for row in values[:-1])
        and all(math.isfinite(float(value)) for row in values for value in row)
        and all(float(value) > 0 for value in model.scales)
    )


def _provenance_integrity(model):
    training = model.training_ids
    evaluation = model.evaluation_ids
    valid_lists = all(
        isinstance(ids, list)
        and bool(ids)
        and all(isinstance(item, str) and bool(item) for item in ids)
        and len(set(ids)) == len(ids)
        for ids in (training, evaluation)
    )
    return {
        'present': bool(training and evaluation),
        'unique': valid_lists,
        'disjoint': bool(valid_lists and not (set(training) & set(evaluation))),
        'valid': bool(valid_lists and not (set(training) & set(evaluation))),
    }


def classify_cost_report(report):
    """Classify cost evidence without trusting a legacy ``measured`` flag."""
    calls = report.get('llm_calls', 0)
    transactions = report.get('transactions', 0)
    observed = isinstance(calls, int) and calls > 0
    return {
        'observed_runtime_usage': observed,
        'calculated_cost_from_observed_usage': bool(observed and 'actual_cost_usd' in report),
        'modeled_counterfactual_present': 'counterfactual_all_cloud_cost_usd' in report,
        'verified_invoice_cost_present': report.get('verified_invoice_cost_usd') is not None,
        'empirical_measurement_eligible': bool(observed and isinstance(transactions, int) and transactions > 0),
        'legacy_measured_flag': report.get('measured'),
    }


def audit_calibration(root: Path):
    model_path = root / 'data/models/calibrator.json'
    metrics_path = root / 'data/models/calibrator_metrics.json'
    cv_path = root / 'data/models/calibrator_cv_metrics.json'
    model = LogisticConfidenceCalibrator.load(str(model_path))
    deployable = True
    schema_error = None
    try:
        model.require_schema('production-confidence-v1')
    except ValueError as exc:
        deployable = False
        schema_error = str(exc)
    metrics = _read(root, 'data/models/calibrator_metrics.json')
    cv = _read(root, 'data/models/calibrator_cv_metrics.json')
    dataset = metrics.get('dataset', {})
    cv_dataset = cv.get('dataset', {})
    in_sample_metrics = metrics.get('metrics', {})
    cv_metrics = cv.get('cv_metrics', {})
    provenance = _provenance_integrity(model)
    in_sample_counts = _confusion_consistent(
        in_sample_metrics, dataset.get('exploit_rows', -1), dataset.get('benign_rows', -1)
    )
    cv_counts = _confusion_consistent(
        cv_metrics, cv_dataset.get('exploit_rows', -1), cv_dataset.get('benign_rows', -1)
    )
    cv_has_ece = any(key in cv_metrics for key in ('ece', 'expected_calibration_error'))
    cv_artifact_complete = all((
        cv_has_ece,
        bool(cv.get('fold_counts')),
        bool(cv.get('input_digests')),
        bool(cv.get('oof_predictions')),
        bool(cv.get('reliability_bins')),
    ))
    model_integrity = _model_integrity(model)
    if not model_integrity:
        status = 'INVALID_MODEL_ARTIFACT'
    elif not deployable:
        status = 'BLOCKED_NON_DEPLOYABLE'
    elif not cv_artifact_complete:
        status = 'INCOMPLETE_CV_EVIDENCE'
    else:
        status = 'LOCAL_SCHEMA_VALID'
    return {
        'status': status,
        'model_path': model_path.as_posix(),
        'metrics_path': metrics_path.as_posix(),
        'cv_metrics_path': cv_path.as_posix(),
        'feature_names_match': model.feature_names == FEATURE_NAMES,
        'model_integrity': model_integrity,
        'schema_id': model.schema_id,
        'deployable_production_schema': deployable,
        'schema_error': schema_error,
        'provenance': provenance,
        'in_sample_counts_consistent': in_sample_counts,
        'in_sample_metric_scope': 'in-sample_same_rows',
        'cv_counts_consistent': cv_counts,
        'cv_has_ece': cv_has_ece,
        'cv_fold_counts_retained': bool(cv.get('fold_counts')),
        'cv_input_digests_retained': bool(cv.get('input_digests')),
        'cv_reliability_bins_retained': bool(cv.get('reliability_bins')),
        'cv_provenance_retained': provenance['valid'],
        'cv_row_level_predictions_retained': bool(cv.get('oof_predictions')),
        'cv_artifact_complete': cv_artifact_complete,
        'metrics_regenerable_from_retained_inputs': False,
    }


def audit_cost(root: Path):
    measured = _read(root, 'reports/claim_evidence/measured_cost_run.json')
    zero_spend = _read(root, 'reports/claim_evidence/cost_zero_spend_proof.json')
    modeled = _read(
        root,
        'reports/canonical_history/snapshots/'
        'b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/'
        'reports/research_results/runtime_cost.json',
    )
    requested = measured.get('requested_runs', {}).get('n100', {})
    computed = modeled.get('computed', {})
    empty_tracker = CostTracker().report()
    empty_tracker_semantics = classify_cost_report(empty_tracker)
    state_path = root / 'reports/claim_evidence/measured_cost_run_state.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    expected_mix = {'1': 50, '2': 30, '3': 20}
    inputs = modeled.get('inputs', {})
    fractions = inputs.get('tier_fractions', {})
    hybrid = (
        fractions.get('tier2', 0) * inputs.get('tier2_hybrid_cost_per_query_usd', 0)
        + fractions.get('tier3', 0) * inputs.get('tier3_cost_per_query_usd', 0)
    )
    cloud = (
        fractions.get('tier2', 0) * inputs.get('tier2_cloud_cost_per_query_usd', 0)
        + fractions.get('tier3', 0) * inputs.get('tier3_cost_per_query_usd', 0)
    )
    arithmetic_consistent = (
        math.isclose(hybrid, computed.get('hybrid_cost_per_query_usd', -1), rel_tol=0, abs_tol=1e-12)
        and math.isclose(cloud, computed.get('cloud_only_cost_per_query_usd', -1), rel_tol=0, abs_tol=1e-12)
        and math.isclose(100 * (cloud - hybrid) / cloud, computed.get('cost_reduction_pct', -1), rel_tol=0, abs_tol=1e-9)
    )
    selection_files = measured.get('input_gate', {}).get('candidate_selection_files', [])
    return {
        'status': 'BLOCKED_EMPIRICAL_EVIDENCE' if requested.get('completed_n') != 100 else 'MEASURED_WORKLOAD_PRESENT',
        'measured_run_status': requested.get('status'),
        'completed_n': requested.get('completed_n'),
        'target_n': requested.get('target_n'),
        'provider_calls': measured.get('provider_gate', {}).get('provider_calls'),
        'measured_saving_fraction': measured.get('measurements', {}).get('measured_saving_fraction'),
        'state_report_consistent': measured == state,
        'selection_manifest_present': bool(selection_files),
        'declared_workload_mix': requested.get('tier_mix'),
        'required_workload_mix': expected_mix,
        'observed_workload_mix_present': bool(measured.get('measurements', {}).get('workload_tier_counts')),
        'pricing_source_present': bool(modeled.get('pricing_source')),
        'pricing_timestamp_present': bool(modeled.get('pricing_verified_at')),
        'paired_quality_outcomes_present': bool(measured.get('measurements', {}).get('quality_outcomes')),
        'paired_rank_outcomes_present': bool(measured.get('measurements', {}).get('rank_outcomes')),
        'zero_spend_status': zero_spend.get('conclusion'),
        'modeled_cost_reduction_pct': computed.get('cost_reduction_pct'),
        'modeled_hybrid_cost_usd': computed.get('hybrid_cost_per_query_usd'),
        'modeled_cloud_only_cost_usd': computed.get('cloud_only_cost_per_query_usd'),
        'old_58_percent_status': modeled.get('correction', {}).get('old_claim_status'),
        'modeled_arithmetic_consistent': arithmetic_consistent,
        'empty_tracker_measured': empty_tracker.get('measured'),
        'empty_tracker_semantics': empty_tracker_semantics,
        'empty_tracker_qualifies_as_empirical_evidence': empty_tracker_semantics['empirical_measurement_eligible'],
        'measured_usage_log_present': bool(measured.get('measurements', {}).get('per_call_log')),
    }


def audit(root: Path):
    calibration = audit_calibration(root)
    cost = audit_cost(root)
    empirical_blocked = (
        calibration['status'] != 'LOCAL_SCHEMA_VALID'
        or cost['status'] == 'BLOCKED_EMPIRICAL_EVIDENCE'
    )
    return {
        'status': 'BLOCKED_EMPIRICAL_EVIDENCE' if empirical_blocked else 'LOCAL_EVIDENCE_COMPLETE',
        'external_effects': False,
        'calibration': calibration,
        'cost': cost,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    report = audit(args.root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if report['status'] == 'BLOCKED_EMPIRICAL_EVIDENCE' else 0


if __name__ == '__main__':
    raise SystemExit(main())
