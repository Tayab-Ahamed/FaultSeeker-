"""Bounded TRAIN-only chain trace probes; never changes acquisition indices.

Every RPC request uses the shared MeteredRPC and cumulative $10 SpendGuard.
No automatic retry, replay, or held-out acquisition is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules['readline'] = None

TARGETS = {
    'bsc': '0x13d19809b19ac512da6d110764caee75e2157ea62cb70937c8d9471afcb061bf',
    'fantom': '0x19315e5b150d0a83e797203bb9c957ec1fa8a6f404f4f761d970cb29a74a5dd6',
    'gnosis': '0x534b84f657883ddc1b66a314e8b392feb35024afdec61dfe8e7c510cfac1a098',
}
SOURCES = {
    'bsc': 'https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/',
    'fantom': 'https://docs.fantom.foundation/build-on-opera/api/public-endpoints',
    'gnosis': 'https://docs.gnosischain.com/tools/RPC%20Providers/',
    'gnosis-gateway': 'https://docs.gnosischain.com/about/networks/mainnet',
}
PUBLIC = {
    'bsc': [('official-public', 'https://bsc-dataseed.bnbchain.org')],
    'fantom': [('official-tracing', 'https://rpcapi-tracing.fantom.network'),
               ('documented-publicnode', 'https://fantom.publicnode.com')],
    'gnosis': [('official-starter', 'https://rpc.gnosischain.com'),
               ('official-gateway', 'https://rpc.gnosis.gateway.fm')],
}


def require_train(identity, split):
    if identity not in split['train_ids'] or identity in split.get('heldout_ids', []):
        raise ValueError('Probe requires frozen TRAIN identity')


class ProbeBudget:
    def __init__(self, maximum=40):
        if not 0 < maximum <= 40:
            raise ValueError('Maximum must be within 1..40')
        self.maximum, self.used = maximum, 0

    def take(self):
        if self.used >= self.maximum:
            raise RuntimeError('Aggregate request cap reached before dispatch')
        self.used += 1


def safe_error(error):
    # Exception messages may contain credentials. Never persist them.
    return {'error_type': type(error).__name__}


def validate_trace(trace, transaction, receipt):
    from scripts.capture_authentic_traces import validate_call_identity
    validate_call_identity(trace, transaction, receipt)
    if str(trace.get('input', '0x')).lower() != str(transaction.get('input', '0x')).lower():
        raise ValueError('Trace calldata differs from canonical transaction')
    if int(trace.get('value', '0x0'), 16) != int(transaction.get('value', '0x0'), 16):
        raise ValueError('Trace value differs from canonical transaction')


def parity_call_tree(rows, transaction, receipt):
    """Lossless call-only Parity tree adaptation with exact identity checks.

    Other Parity entry types require an explicit adapter, never guessed fields.
    The original provider response is always retained separately.
    """
    nodes, expected_children = {}, {}
    for row in rows:
        if (row.get('transactionHash', '').lower() != transaction['hash'].lower()
                or row.get('blockHash', '').lower() != transaction['blockHash'].lower()
                or row.get('blockNumber') != int(transaction['blockNumber'], 16)
                or row.get('transactionPosition') != int(transaction['transactionIndex'], 16)):
            raise ValueError('Parity block/transaction identity mismatch')
        path = tuple(row['traceAddress'])
        if path in nodes or any(type(n) is not int or n < 0 for n in path):
            raise ValueError('Parity path is duplicate or invalid')
        action = row.get('action', {})
        if row.get('type') != 'call' or action.get('callType') not in ('call', 'staticcall', 'delegatecall', 'callcode'):
            raise ValueError('Unsupported Parity entry type')
        node = dict(action)
        node['type'] = node.pop('callType').upper()
        node.update(row.get('result', {}))
        if row.get('error'):
            node['error'] = row['error']
        nodes[path] = node
        expected_children[path] = row['subtraces']
    if () not in nodes:
        raise ValueError('Parity root missing')
    for path in sorted(nodes, key=lambda p: (len(p), p)):
        children = sorted(p for p in nodes if len(p) == len(path) + 1 and p[:-1] == path)
        if [p[-1] for p in children] != list(range(expected_children[path])):
            raise ValueError('Parity subtrace completeness mismatch')
        if path and path[:-1] not in nodes:
            raise ValueError('Parity orphan path')
        if children:
            nodes[path]['calls'] = [nodes[p] for p in children]
    validate_trace(nodes[()], transaction, receipt)
    return nodes[()]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def classify(error):
    message = str(error.get('message', '')).lower()
    for needle, category in [('not found', 'NOT_FOUND'), ('not available', 'METHOD_UNAVAILABLE'),
                             ('not supported', 'METHOD_UNAVAILABLE'), ('limit', 'RATE_OR_RESOURCE_LIMIT'),
                             ('historical', 'HISTORICAL_DATA_UNAVAILABLE'), ('pruned', 'HISTORICAL_DATA_UNAVAILABLE')]:
        if needle in message:
            return category
    return 'RPC_REJECTED'


def run(output, max_requests=40):
    from dotenv import dotenv_values
    from scripts import replay_historical_opcodes as metering
    from scripts.rebuild_authentic_cohort import drpc_url
    from benchmark.research_protocol import bind, read_bound, load_train

    split = json.loads((ROOT / 'benchmark/eval_split.json').read_text(encoding='utf-8'))
    admitted = load_train(split, ROOT)
    rows = {r['chain'] + ':' + r['txn_hash']: r for r in admitted}
    for chain, tx in TARGETS.items():
        require_train(chain + ':' + tx, split)
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'probe.json').exists():
        raise ValueError('Existing probe is immutable; do not rerun blindly')
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'sources': [], 'observations': [],
              'scope': 'Three specified frozen TRAIN identities only; call traces are not opcode/storage evidence.'}
    for name, url in SOURCES.items():
        source = {'url': url}
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read()
            path = output / 'sources' / (name + '.html')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            source['artifact'] = bind(path, ROOT)
        except Exception as error:
            source.update(safe_error(error))
        report['sources'].append(source)
    budget, meters = ProbeBudget(max_requests), []
    authorized = dotenv_values(ROOT / '.env').get('DRPC_RPC_URL')
    # Exact read-only Parity method extension; forwarding and spend control remain
    # in the existing shared meter. Never modifies the source allowlist file.
    metering.READ_METHODS.add('trace_transaction')
    try:
        for chain, tx in TARGETS.items():
            row = rows[chain + ':' + tx]
            rpc = json.loads(read_bound(row['rpc'], ROOT).decode('utf-8'))
            endpoints = list(PUBLIC[chain])
            if chain == 'bsc' and authorized:
                endpoints.insert(0, ('configured-drpc', drpc_url(authorized, chain)))
            captured = False
            for label, endpoint in endpoints:
                meter = metering.MeteredRPC(endpoint, ROOT / 'data/research/spend_ledger.json', max_requests=40)
                meters.append(meter)
                observation = {'identity': chain + ':' + tx, 'endpoint_label': label, 'attempts': []}
                report['observations'].append(observation)
                def request(method, params):
                    budget.take()
                    return meter.forward({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
                try:
                    response = request('eth_chainId', [])
                    if response.get('error'):
                        observation.update(status=classify(response['error']), rpc_code=response['error'].get('code'))
                        continue
                    if int(response.get('result', '0x0'), 16) != rpc['chain_id']:
                        observation['status'] = 'WRONG_CHAIN'
                        continue
                    observation['chain_id_verified'] = rpc['chain_id']
                    for method, params in [('debug_traceTransaction', [tx, {'tracer': 'callTracer', 'timeout': '15s'}]),
                                           ('trace_transaction', [tx])]:
                        attempt = {'method': method}
                        observation['attempts'].append(attempt)
                        try:
                            response = request(method, params)
                            if response.get('error'):
                                attempt.update(status=classify(response['error']), rpc_code=response['error'].get('code'))
                                continue
                            result = response.get('result')
                            if method == 'debug_traceTransaction':
                                validate_trace(result, rpc['transaction'], rpc['receipt'])
                            elif not isinstance(result, list) or not result or any(
                                item.get('transactionHash', '').lower() != tx for item in result):
                                raise ValueError('Parity trace missing exact transaction binding')
                            path = output / 'captures' / (chain + '-' + method + '.json.gz')
                            path.parent.mkdir(parents=True, exist_ok=True)
                            capture = {'chain': chain, 'transaction_hash': tx, 'method': method, 'result': result,
                                       'rpc_identity': row['rpc'], 'endpoint_label': label,
                                       'storage_trace_complete': False}
                            path.write_bytes(gzip.compress(json.dumps(capture).encode('utf-8'), mtime=0))
                            attempt.update(status='CAPTURED', artifact=bind(path, ROOT))
                            captured = True
                            break
                        except Exception as error:
                            attempt.update(status='FAILED', **safe_error(error))
                    observation['status'] = 'CAPTURED' if captured else 'NO_TRACE'
                except Exception as error:
                    observation.update(status='FAILED', **safe_error(error))
                finally:
                    observation['accounting'] = meter.summary()
                    report['outbound_rpc_requests'] = sum(m.count for m in meters)
                    report['estimated_cost_usd'] = report['outbound_rpc_requests'] * 6 / 1_000_000
                    report['cumulative_ledger_estimate_usd'] = meter.guard.report()['spent_usd']
                    report['billing_confirmed'] = False
                    write(output / 'probe.json', report)
                if captured:
                    break
    finally:
        metering.READ_METHODS.discard('trace_transaction')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--max-requests', type=int, default=40)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/cohort_rebuild_v2/chain_trace_probe')
    args = parser.parse_args()
    if not args.execute_live:
        raise SystemExit('No RPC dispatched; explicit --execute-live required.')
    result = run(args.output, args.max_requests)
    print(json.dumps({k: result[k] for k in ('outbound_rpc_requests', 'estimated_cost_usd', 'cumulative_ledger_estimate_usd')}))
