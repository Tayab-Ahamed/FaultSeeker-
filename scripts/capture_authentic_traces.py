"""Capture actual call traces and historical contract code for admitted identities.

No opcode or storage observation is synthesized from call traces. Complexity is
the count of unique (contract address, input selector) pairs, including a single
empty selector for a contract's fallback/receive path. EOAs are excluded using
historical eth_getCode, not an address-name heuristic.
"""
import argparse
from datetime import datetime, timezone
import uuid
import gzip
import json
import re
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from dotenv import dotenv_values
from benchmark.research_protocol import (bind, read_bound, write_json, admit, identity,
    acquisition_records, acquisition_directory, load_train_split, load_acquisition_indexes)
from scripts.rebuild_authentic_cohort import BASE, drpc_url
from scripts.replay_historical_opcodes import MeteredRPC


def walk(node):
    yield node
    for child in node.get('calls',[]):
        yield from walk(child)


def validate_call_identity(trace, transaction, receipt=None):
    if not isinstance(trace,dict) or trace.get('error'):
        raise ValueError('Successful call trace required')
    expected=dict(transaction)
    if transaction.get('to') is None:
        if trace.get('type') not in ('CREATE','CREATE2') or not (receipt or {}).get('contractAddress'):
            raise ValueError('Contract creation identity requires its canonical receipt')
        expected['to']=receipt['contractAddress']
    for field in ('from','to'):
        if str(trace.get(field,'')).lower()!=str(expected.get(field,'')).lower():
            raise ValueError('Call trace transaction identity mismatch')


def complexity_observation(trace, code):
    frames=list(walk(trace))
    unique=set()
    for frame in frames:
        address=frame.get('to','').lower()
        if not address:
            raise ValueError('Call target code cannot be verified')
        if address not in code or not isinstance(code[address],str) or not code[address].startswith('0x'):
            raise ValueError('Historical contract code missing')
        if code[address]=='0x' and frame.get('calls'):
            raise ValueError('Historical code missing for an executed contract, possibly destroyed')
        if code[address]!='0x':
            unique.add((address,frame.get('input','0x')[:10].lower()))
    count=len(unique)
    return {'unique_function_calls':count,'trace_frames':len(frames),
        'complexity_class':'Simple' if count<=5 else 'Moderate' if count<=50 else 'Complex' if count<=500 else 'Exceptionally Complex',
        'definition':'Unique contract address and input selector pairs, verified with post-block code; empty input denotes fallback/receive. EOAs excluded. Self-destructed targets may need pre-state code.',
        'unique_functions':[{'address':a,'selector':s} for a,s in sorted(unique)]}


def _validated_cached_capture(binding, row):
    raw = read_bound(binding, ROOT)
    capture = json.loads(gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw)
    if (capture.get('transaction_hash') != row['txn_hash'] or capture.get('chain') != row['chain']
            or capture.get('rpc_identity') != row['rpc']):
        raise ValueError('Cached capture identity or bound RPC mismatch')
    rpc = json.loads(read_bound(row['rpc'], ROOT))
    validate_call_identity(capture['raw_trace']['call'], rpc['transaction'], rpc['receipt'])
    return capture


def run(split_file=None, requested_ids=None, max_requests=1000):
    if type(max_requests) is not int or not 1 <= max_requests <= 1000:
        raise ValueError('Request limit must be 1..1000')
    rows = acquisition_records(ROOT, BASE / 'admitted_records.json', split_file=split_file)
    allowed = {identity(row) for row in rows}
    if requested_ids is not None and (not requested_ids or not set(requested_ids) <= allowed):
        raise ValueError('Requested identities must belong to selected TRAIN')
    if requested_ids is not None:
        rows = [row for row in rows if identity(row) in requested_ids]
    if not rows:
        raise ValueError('No accepted TRAIN acquisition identities')
    frozen = split_file is not None or (ROOT / 'benchmark/eval_split.json').exists()
    split_binding, cache = None, {}
    if frozen:
        split_path, _ = load_train_split(ROOT, split_file)
        split_binding = bind(split_path, ROOT)
        indexes, _ = load_acquisition_indexes(ROOT, split_file)
        cache = indexes['trace']
    namespace = acquisition_directory(ROOT, split_file) if split_file is not None else BASE
    index = namespace / ('trace_acquisition_train.json' if frozen else 'trace_acquisition.json')
    prior = []
    history = []
    if index.exists():
        data = json.loads(index.read_text())
        if split_file is not None:
            data = json.loads(read_bound(data['snapshot'], ROOT))
        prior = data.get('attempts', []) if isinstance(data, dict) else data
        history = data.get('history', []) if isinstance(data, dict) else list(prior)
    latest = {record['identity']: record for record in prior}
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    run_dir = namespace / 'runs' / run_id
    attempts = []
    report = {'run_id': run_id, 'status': 'COMPLETE', 'split': split_binding,
              'requested_ids': [identity(row) for row in rows], 'attempts': attempts,
              'outbound_rpc_requests': 0, 'heldout_used': False}

    def checkpoint(result):
        attempts.append(result)
        latest[result['identity']] = result
        history.append(result)
        snapshot = {'schema': 1, 'run_id': run_id, 'split': split_binding,
                    'attempts': list(latest.values()), 'history': history,
                    'status': report['status']}
        if split_file is not None:
            target = run_dir / ('index-%04d.json' % len(attempts))
            write_json(target, snapshot)
            pointer = {'schema': 1, 'split': split_binding, 'snapshot': bind(target, ROOT)}
            temporary = index.with_name(index.name + '.' + run_id + '.tmp')
            write_json(temporary, pointer)
            temporary.replace(index)
            report['index'] = bind(target, ROOT)
        else:
            write_json(index, list(latest.values()))
            report['index'] = bind(index, ROOT)
        write_json(run_dir / 'summary.json', report)

    for row in rows:
        if not admit(row, ROOT)['accepted']:
            raise ValueError('Admission no longer valid')
        key = identity(row)
        result = {'identity': key, 'status': 'UNAVAILABLE'}
        meter, phase = None, 'cached-capture-validation'
        try:
            cached = cache.get(key, {}).get('artifact') or row.get('trace')
            if cached:
                capture = _validated_cached_capture(cached, row)
                result.update(status='RECORDED', artifact=cached,
                              complexity=capture.get('complexity'),
                              accounting={'outbound_rpc_requests': 0, 'estimated_cost_usd': 0})
                checkpoint(result)
                continue
            phase = 'endpoint-configuration'
            endpoint = dotenv_values(ROOT / '.env').get('DRPC_RPC_URL')
            if not endpoint:
                raise ValueError('DRPC_RPC_URL required')
            remaining = max_requests - report['outbound_rpc_requests']
            if remaining <= 0:
                raise RuntimeError('Request limit reached before dispatch')
            meter = MeteredRPC(drpc_url(endpoint, row['chain']),
                              ROOT / 'data/research/spend_ledger.json', max_requests=remaining)
            rpc = json.loads(read_bound(row['rpc'], ROOT))
            phase = 'eth_chainId'
            if int(meter.rpc('eth_chainId', []), 16) != rpc['chain_id']:
                raise ValueError('Wrong RPC chain')
            phase = 'debug_traceTransaction'
            response = meter.forward({'jsonrpc': '2.0', 'id': 1, 'method': phase,
                                      'params': [row['txn_hash'], {'tracer': 'callTracer'}]})
            if response.get('error') or not isinstance(response.get('result'), dict):
                code = (response.get('error') or {}).get('code')
                if type(code) is int:
                    result['rpc_error_code'] = code
                raise RuntimeError('callTracer returned no trace')
            trace = response['result']
            phase = 'call-trace-validation'
            validate_call_identity(trace, rpc['transaction'], rpc['receipt'])
            addresses = sorted({frame.get('to', '').lower() for frame in walk(trace)} - {''})
            code = {}
            for address in addresses:
                phase = 'eth_getCode'
                code[address] = meter.rpc('eth_getCode', [address, rpc['receipt']['blockNumber']])
            capture = {'transaction_hash': row['txn_hash'], 'chain': row['chain'],
                       'raw_trace': {'call': trace}, 'storage_trace_complete': False,
                       'rpc_identity': row['rpc'], 'historical_code': code,
                       'capture_version': 'live-callTracer-with-historical-code-v1'}
            try:
                capture['complexity'] = complexity_observation(trace, code)
            except ValueError:
                capture['complexity'] = {'complexity_class': 'UNRECOVERED',
                                         'reason': 'Complete historical code verification unavailable'}
            phase = 'capture-persistence'
            target = run_dir / 'traces' / row['chain'] / (row['txn_hash'] + '.json.gz')
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(gzip.compress(json.dumps(capture).encode(), mtime=0))
            result.update(status='CAPTURED_CALL_TRACE', artifact=bind(target, ROOT),
                          complexity=capture['complexity'])
        except Exception as error:
            result.update(error_type=type(error).__name__, phase=phase)
            # MeteredRPC.rpc generates this controlled form; preserve only the
            # numeric RPC code, never arbitrary exception or endpoint text.
            controlled = re.fullmatch(
                r'(eth_chainId|eth_getCode) failed \(RPC code (-?\d{1,10})\)', str(error))
            if isinstance(error, RuntimeError) and controlled and controlled[1] == phase:
                result['rpc_error_code'] = int(controlled[2])
            status = getattr(error, 'http_status', None)
            if type(status) is int and 100 <= status <= 599:
                result['http_status'] = status
            report['status'] = 'STOPPED_ON_ERROR'
        if meter is not None:
            result['accounting'] = meter.summary()
        else:
            result['accounting'] = {'outbound_rpc_requests': 0, 'estimated_cost_usd': 0}
        report['outbound_rpc_requests'] += result['accounting']['outbound_rpc_requests']
        checkpoint(result)
        print(row['chain'], row['txn_hash'][:12], result['status'], flush=True)
        if report['status'] == 'STOPPED_ON_ERROR':
            break
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Explicit permission to dispatch metered RPC reads')
    parser.add_argument('--split-file', help='Explicit workspace-relative frozen TRAIN split')
    parser.add_argument('--identity', action='append', help='Only this selected TRAIN chain:transaction identity')
    parser.add_argument('--max-requests', type=int, default=1000)
    args = parser.parse_args(argv)
    if not args.live:
        parser.error('Explicit --live required; no request dispatched')
    return run(split_file=args.split_file, requested_ids=args.identity, max_requests=args.max_requests)


if __name__ == '__main__':
    main()
