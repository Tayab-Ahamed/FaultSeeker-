"""Train-only production Stage 1 and function ranking on real recorded executions.

Stage 2 models and Eq.4 function confidence are deliberately not measured by
this command. Missing inputs and coverage remain explicit. This is a production
execution bridge and a preflight, not a substitute final-system experiment.
"""
import argparse
from collections import Counter
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import socket
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault('readline', None)
from benchmark.captured_inputs import load_train_inputs, load_train_split
from benchmark.research_protocol import append_experiment, bind, identity, load_train, write_json, load_acquisition_indexes
from benchmark.paper_experiments import confusion_metrics
from faultseeker.function_analysis.function_ranker import FunctionRanker
from scripts.run_authentic_research import snapshot_system, system_identity

BASE = Path('reports/cohort_rebuild_v2')


@contextmanager
def no_network():
    original = socket.socket.connect
    attempts = [0]
    def refuse(*args, **kwargs):
        attempts[0] += 1
        raise RuntimeError('Recorded production execution prohibits network I/O')
    socket.socket.connect = refuse
    try:
        yield attempts
    finally:
        socket.socket.connect = original


def observe_stage_one(root, requested_identity, cache_dir, split_file=None):
    started = time.perf_counter()
    stream = io.StringIO()
    with no_network() as attempts, redirect_stdout(stream):
        inputs = load_train_inputs(root, requested_identity, require_opcodes=False, split_file=split_file)
        orchestrator = inputs.orchestrator(cache_dir)
        tx, chain = inputs.structured['transaction_hash'], inputs.structured['chain']
        result, sequence, info = orchestrator.run(tx, chain)
        if result is None:
            raise RuntimeError('Production forensics did not complete')
        ranking = FunctionRanker().rank(result, {
            'transaction_hash': tx, 'chain': chain, 'trace': result.trace,
            'repeated_patterns': result.repeated_patterns,
            'function_call_loc_memo': result.function_call_loc_memo})
    if attempts[0]:
        raise RuntimeError('Network attempted during recorded production execution')
    tier = result.signals['reentrancy']['tier']
    return {'identity': requested_identity, 'pipeline_stage': 'production-stage-one-and-ranker',
        'forensics': {'report': result.to_dict(include_internal=True), 'signals': result.signals,
                      'rule_verdict': result.rule_verdict, 'rule_confidence': result.rule_confidence,
                      'matched_rule': result.matched_rule, 'vuln_type_hint': result.vuln_type_hint},
        'ranking': asdict(ranking), 'coverage': result.signals['coverage'],
        'trace_coverage': sequence['trace_coverage'], 'evidence': inputs.evidence,
        'storage_proof': inputs.proof, 'reentrancy_component_prediction': tier in {
            'HIGH_RISK_REENTRANCY', 'CONFIRMED_REENTRANCY'},
        'stage2_executed': False, 'stage3_executed': False, 'network_attempts': attempts[0],
        'duration_seconds': time.perf_counter() - started,
        'duration_scope': 'Bound input loading, real production Stage 1 and deterministic function ranker; no provider latency',
        'stdout': stream.getvalue()}


def run_train(root=ROOT, requested_ids=None, split_file=None):
    root = Path(root).resolve()
    split_path, split = load_train_split(root, split_file)
    if requested_ids and not set(requested_ids) <= set(split['train_ids']):
        raise ValueError('Only train identities may enter production preflight')
    rows = load_train(split, root)
    if requested_ids:
        rows = [r for r in rows if identity(r) in requested_ids]
    if not rows:
        raise ValueError('Nonempty train population required')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    out = root / BASE / 'production_runs' / run_id
    out.mkdir(parents=True, exist_ok=False)
    system = system_identity([ROOT / 'benchmark/captured_inputs.py', Path(__file__).resolve()])
    write_json(out / 'system.json', system)
    config = {'experiment': 'recorded-production-stage1-v1', 'system_sha256': system['sha256'],
        'system_snapshot': bind(snapshot_system(system, out), root), 'split': bind(split_path, root),
        'manifest': split.get('manifest') or bind(root / 'benchmark/cohort_manifest.json', root),
        'acquisition_indexes': load_acquisition_indexes(root, split_file)[1],
        'algorithms': 'Actual ForensicsOrchestrator, TraceAnalyzer, SignalExtractor, rule classifier, address/fund-flow classifiers and FunctionRanker',
        'network_policy': 'Every socket connect refused; no provider or RPC dispatch permitted',
        'population': 'Frozen train only; incomplete cases excluded explicitly, not classified negative',
        'stage2_not_executed': True, 'paper_weights_and_thresholds': 'unchanged'}
    common = {'seed': split['seed'], 'config': config, 'run_id': run_id}
    log = root / BASE / 'experiments_log.json'
    append_experiment(log, split, dict(common, kind='dispatch-train', metrics=None, sample_ids=[]))
    observed, missing = [], []
    for row in rows:
        key = identity(row)
        try:
            record = observe_stage_one(root, key, out / 'forensics', split_file=split_path if split_file is not None else None)
            # The outcome is joined only after production analysis returns.
            record['reentrancy_label'] = row['reentrancy_label']
            observed.append(record)
            write_json(out / (row['chain'] + '-' + row['txn_hash'] + '.json'), record)
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            missing.append({'identity': key, 'error_type': type(error).__name__, 'reason': str(error)[:300]})
    metrics = None
    if observed:
        metrics = {'reentrancy_component': confusion_metrics([r['reentrancy_label'] for r in observed],
            [r['reentrancy_component_prediction'] for r in observed]),
            'rule_verdict_counts': dict(Counter(r['forensics']['rule_verdict'] for r in observed))}
    summary = {'run_id': run_id, 'scope': 'Production Stage 1 and deterministic function ranker only',
        'config': config, 'coverage': {'observed': len(observed), 'requested_train': len(rows)},
        'metrics': metrics, 'missing': missing,
        'observations': [{'identity': r['identity'], 'rule_verdict': r['forensics']['rule_verdict'],
            'reentrancy_component_prediction': r['reentrancy_component_prediction'],
            'trace_coverage': r['trace_coverage'], 'coverage': r['coverage'],
            'ranked_address_count': len(r['ranking']['address_list'])} for r in observed],
        'unmeasured': {'full_system_f1': 'Stage2/3 not executed; no negative general-exploit population in this train cohort',
            'localization': 'No independently sourced complete address/signature function target records or source-linked line targets',
            'hybrid_cost_savings': 'No reachable installed Ollama model established; no paired billed production queries',
            'table_vi': 'No production Stage3 per-function confidence component records',
            'guidance': 'No complete 20-case source-targeted paired guidance population'},
        'heldout_used': False, 'final_exam_dispatched': False, 'network_requests': 0}
    path = out / 'summary.json'
    write_json(path, summary)
    append_experiment(log, split, dict(common, kind='scored-train' if observed else 'blocked-preflight',
        sample_ids=[r['identity'] for r in observed], metrics=metrics, evidence=bind(path, root), missing=missing))
    print('Production Stage1 train run', run_id, summary['coverage'], metrics, flush=True)
    for record in missing:
        print('Unavailable', record['identity'], record['reason'], flush=True)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identity', action='append', help='Optional frozen chain:transaction identity')
    parser.add_argument('--split-file', help='Explicit workspace-relative frozen split; default benchmark/eval_split.json')
    args = parser.parse_args(argv)
    return run_train(requested_ids=args.identity, split_file=args.split_file)


if __name__ == '__main__':
    main()
