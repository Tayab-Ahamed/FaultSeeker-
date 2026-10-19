"""Audit retained calibration and cost evidence without external effects.

This command reads committed/local artifacts only.  It does not load dotenv,
contact providers, train a model, write reports, or alter research batches.
Passing local integrity checks deliberately does not promote blocked empirical
claims to reproduced results.
"""
from __future__ import annotations

import argparse
import json
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
    in_sample_counts = _confusion_consistent(
        in_sample_metrics, dataset.get('exploit_rows', -1), dataset.get('benign_rows', -1)
    )
    cv_counts = _confusion_consistent(
        cv_metrics, cv_dataset.get('exploit_rows', -1), cv_dataset.get('benign_rows', -1)
    )
    cv_has_ece = any(key in cv_metrics for key in ('ece', 'expected_calibration_error'))
    return {
        'status': 'BLOCKED_NON_DEPLOYABLE' if not deployable else 'LOCAL_SCHEMA_VALID',
        'model_path': model_path.as_posix(),
        'metrics_path': metrics_path.as_posix(),
        'cv_metrics_path': cv_path.as_posix(),
        'feature_names_match': model.feature_names == FEATURE_NAMES,
        'schema_id': model.schema_id,
        'deployable_production_schema': deployable,
        'schema_error': schema_error,
        'in_sample_counts_consistent': in_sample_counts,
        'in_sample_metric_scope': 'same-data aggregate unless separate provenance is supplied',
        'cv_counts_consistent': cv_counts,
        'cv_has_ece': cv_has_ece,
        'cv_provenance_retained': bool(model.training_ids and model.evaluation_ids),
        'cv_row_level_predictions_retained': False,
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
    empty_tracker_measured = CostTracker().report().get('measured')
    return {
        'status': 'BLOCKED_EMPIRICAL_EVIDENCE' if requested.get('completed_n') != 100 else 'MEASURED_WORKLOAD_PRESENT',
        'measured_run_status': requested.get('status'),
        'completed_n': requested.get('completed_n'),
        'target_n': requested.get('target_n'),
        'provider_calls': measured.get('provider_gate', {}).get('provider_calls'),
        'measured_saving_fraction': measured.get('measurements', {}).get('measured_saving_fraction'),
        'zero_spend_status': zero_spend.get('conclusion'),
        'modeled_cost_reduction_pct': computed.get('cost_reduction_pct'),
        'modeled_hybrid_cost_usd': computed.get('hybrid_cost_per_query_usd'),
        'modeled_cloud_only_cost_usd': computed.get('cloud_only_cost_per_query_usd'),
        'old_58_percent_status': modeled.get('correction', {}).get('old_claim_status'),
        'empty_tracker_measured': empty_tracker_measured,
        'measured_usage_log_present': bool(measured.get('measurements', {}).get('per_call_log')),
    }


def audit(root: Path):
    calibration = audit_calibration(root)
    cost = audit_cost(root)
    empirical_blocked = (
        calibration['status'] == 'BLOCKED_NON_DEPLOYABLE'
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
