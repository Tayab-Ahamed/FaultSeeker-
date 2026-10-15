"""Execute genuine train-only component experiments on hash-bound captures.

This command cannot load the held-out partition or dispatch the final exam.
Reentrancy component scores are not overall exploit-detection performance.
Missing observations stay missing and are never converted to negative outcomes.
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault('readline', None)
from benchmark.detector_experiments import detector_observation
from benchmark.paper_experiments import confusion_metrics
from benchmark.research_protocol import (
    admit, append_experiment, bind, canonical, identity, load_train, read_bound, sha, write_json,
)
from scripts.capture_authentic_traces import validate_call_identity
from scripts.replay_historical_opcodes import validate_recorded_capture

BASE = Path('reports/cohort_rebuild_v2')
VARIANTS = ('structural', 'repeated', 'full')


def system_identity():
    paths = sorted((ROOT / 'faultseeker').rglob('*.py')) + [
        ROOT / 'benchmark/detector_experiments.py', ROOT / 'benchmark/paper_experiments.py',
        ROOT / 'benchmark/research_protocol.py', Path(__file__).resolve(),
        ROOT / 'scripts/replay_historical_opcodes.py', ROOT / 'scripts/capture_authentic_traces.py',
    ]
    files = [bind(path, ROOT) for path in paths]
    return {'sha256': sha(canonical(files)), 'files': files}


def _capture(binding, row, root, full=False):
    raw = read_bound(binding, root)
    if raw.startswith(b'\x1f\x8b'):
        raw = gzip.decompress(raw)
    capture = json.loads(raw)
    if capture.get('transaction_hash') != row['txn_hash'] or capture.get('chain') != row['chain']:
        raise ValueError('Capture transaction identity mismatch')
    rpc = json.loads(read_bound(row['rpc'], root))
    validate_call_identity(capture['raw_trace']['call'], rpc['transaction'], rpc['receipt'])
    if full:
        # This validation checks canonical prefix, receipt, signed envelopes,
        # complete normalization and storage attribution against raw opcodes.
        validate_recorded_capture(root / binding['path'], row['txn_hash'])
    # Never pass annotations, source publisher names, expected functions or labels
    # to a detector. Only the captured execution tree/opcodes enter analysis.
    return {'raw_trace': capture['raw_trace']}


def run_train(root=ROOT):
    root = Path(root).resolve()
    split_path = root / 'benchmark/eval_split.json'
    split = json.loads(split_path.read_text())
    if sha((root / 'benchmark/cohort_manifest.json').read_bytes()) != split['manifest_sha256']:
        raise ValueError('Frozen manifest digest mismatch')
    rows = load_train(split, root)
    if not rows:
        raise ValueError('No accepted training records')
    for row in rows:
        if not admit(row, root)['accepted'] or type(row.get('reentrancy_label')) is not bool:
            raise ValueError('Invalid train admission or reentrancy annotation')
    index_path = root / BASE / 'trace_acquisition_train.json'
    trace_index = json.loads(index_path.read_text()) if index_path.exists() else []
    by_id = {record['identity']: record for record in trace_index}
    if len(by_id) != len(trace_index) or not set(by_id) <= set(split['train_ids']):
        raise ValueError('Acquisition index contains duplicate or non-train identities')
    opcode_path = root / BASE / 'opcode_acquisition_train.json'
    opcode_index = json.loads(opcode_path.read_text()).get('attempts', []) if opcode_path.exists() else []
    opcodes = {record['identity']: record for record in opcode_index}
    if len(opcodes) != len(opcode_index) or not set(opcodes) <= set(split['train_ids']):
        raise ValueError('Opcode index contains duplicate or non-train identities')
    system = system_identity()
    config = {'experiment': 'reentrancy-components-v1', 'variants': list(VARIANTS),
              'positive_rule': 'HIGH_RISK_REENTRANCY or CONFIRMED_REENTRANCY for structural/full',
              'repeated_rule': 'address appears more than once outside STATICCALL frames',
              'thresholds': 'unchanged production paper-mode values',
              'system_sha256': system['sha256'], 'split': bind(split_path, root),
              'population': 'all frozen train identities; only available evidence is scored',
              'no_overall_f1_inference': True}
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    out = root / BASE / 'experiments' / run_id
    out.mkdir(parents=True, exist_ok=False)
    log = root / BASE / 'experiments_log.json'
    common = {'seed': split['seed'], 'config': config, 'run_id': run_id}
    write_json(out / 'system.json', system)
    append_experiment(log, split, dict(common, kind='dispatch-train', sample_ids=[], metrics=None))
    result = {'run_id': run_id, 'scope': 'train-only reentrancy components; not overall system F1',
              'frozen_train_n': len(rows), 'config': config, 'variants': {},
              'unmeasured': {'overall_system_f1': 'No full-system production outcomes in this component experiment',
                'cost_savings': 'No paired billed production inference observations',
                'localization': 'No complete source-linked function ground truth and executed rankings',
                'table_vi': 'No production per-function confidence component observations'},
              'heldout_exam_dispatched': False}
    for variant in VARIANTS:
        observations, missing = [], []
        for row in rows:
            key = identity(row)
            record = opcodes.get(key, {}) if variant == 'full' else by_id.get(key, {})
            binding = record.get('artifact') if variant == 'full' else record.get('artifact', row.get('trace'))
            if not binding:
                missing.append({'identity': key, 'reason': 'No bound canonical opcode capture' if variant == 'full' else 'No bound call trace'})
                continue
            try:
                capture = _capture(binding, row, root, full=variant == 'full')
                observation = detector_observation(capture, variant)
                if type(observation.get('predicted_exploit')) is not bool:
                    raise ValueError('Detector did not produce a boolean observation')
                observations.append(dict(observation, identity=key,
                    label=row['reentrancy_label'], label_scope='independently sourced reentrancy root cause',
                    capture_artifact=binding))
            except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
                missing.append({'identity': key, 'reason': str(error)[:300], 'error_type': type(error).__name__})
        metrics = confusion_metrics([r['label'] for r in observations],
                                    [r['predicted_exploit'] for r in observations]) if observations else None
        summary = {'metrics': metrics, 'observations': observations, 'missing': missing,
                   'coverage': {'scored': len(observations), 'eligible_train': len(rows)},
                   'contains_both_classes': len({r['label'] for r in observations}) == 2,
                   'status': 'SCORED_COMPONENT' if observations else 'BLOCKED_BY_MISSING_CAPTURE',
                   'failures': [{'identity': r['identity'], 'expected_reentrant': r['label'],
                                 'observed_reentrant': r['predicted_exploit'], 'detail': r['detector_result']}
                                for r in observations if r['label'] != r['predicted_exploit']]}
        result['variants'][variant] = summary
        artifact = out / (variant + '.json')
        write_json(artifact, summary)
        append_experiment(log, split, dict(common,
            kind='scored-train' if observations else 'blocked-preflight',
            sample_ids=[r['identity'] for r in observations], metrics=metrics,
            variant=variant, evidence=bind(artifact, root), coverage=summary['coverage'], missing=missing))
    write_json(out / 'summary.json', result)
    print('Train experiment', run_id, 'eligible', len(rows), flush=True)
    for variant, value in result['variants'].items():
        print(variant, value['status'], value['coverage'], value['metrics'], flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    run_train()
