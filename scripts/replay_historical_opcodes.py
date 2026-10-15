"""Counted, opt-in historical Ethereum replay through a localhost-only RPC proxy.

All upstream calls, including Anvil's lazy archive reads, share the experiment
spend ledger. Signed block-prefix transactions are replayed without balance,
nonce, code, storage, signature or gas-check overrides.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if os.name == 'nt':
    sys.modules.setdefault('readline', None)

from dotenv import dotenv_values
from faultseeker.core.spend_guard import SpendGuard, BudgetApprovalRequired

REENTRANT = '0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6'
COMPARISON = '0x90b468608fbcc7faef46502b198471311baca3baab49242a4a85b73d4924379b'
READ_METHODS = {
    'eth_chainId', 'net_version', 'web3_clientVersion', 'eth_blockNumber',
    'eth_getBlockByNumber', 'eth_getBlockByHash', 'eth_getBalance',
    'eth_getCode', 'eth_getStorageAt', 'eth_getTransactionCount',
    'eth_getTransactionByHash', 'eth_getTransactionReceipt',
    'eth_getRawTransactionByHash', 'eth_getProof', 'eth_getBlockReceipts',
    'eth_getTransactionByBlockHashAndIndex', 'eth_getTransactionByBlockNumberAndIndex',
    'eth_call', 'eth_getLogs', 'debug_traceTransaction', 'trace_replayTransaction',
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())


class MeteredRPC:
    def __init__(self, url, ledger, max_requests=5000):
        self.url = url
        self.max_requests = max_requests
        self.count = 0
        self.methods = Counter()
        self.errors = []
        self.lock = threading.Lock()
        self.guard = SpendGuard(ledger_path=ledger, limit_usd=10,
                                pricing={'drpc-request': {'input': 6, 'output': 0}})

    def forward(self, payload):
        calls = payload if isinstance(payload, list) else [payload]
        if not calls or any(not isinstance(c, dict) or c.get('method') not in READ_METHODS for c in calls):
            raise ValueError('Upstream proxy permits only allowlisted read RPC methods')
        with self.lock:
            if self.count + len(calls) > self.max_requests:
                raise RuntimeError('RPC request limit reached before dispatch')
            reservation = self.guard.reserve('drpc-request', len(calls), 0)
            self.count += len(calls)
            self.methods.update(c['method'] for c in calls)
        failed = True
        try:
            request = Request(self.url, data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'})
            try:
                with urlopen(request, timeout=30) as response:
                    data = json.load(response)
            except HTTPError as error:
                # Never serialize an exception containing a credential-bearing URL.
                raise RuntimeError(f'Upstream HTTP {error.code}') from None
            failed = any(c.get('error') for c in (data if isinstance(data, list) else [data]))
            return data
        finally:
            self.guard.settle(reservation, failed=failed)

    def rpc(self, method, params):
        data = self.forward({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        if data.get('error') or data.get('result') is None:
            raise RuntimeError(f'{method} failed (RPC code {data.get("error", {}).get("code")})')
        return data['result']

    def summary(self):
        budget = self.guard.report()
        prior = [e for e in budget['events'] if e.get('event') == 'external-estimate'
                 and e.get('source') == 'pre-metering-drpc-probes-2026-10-15']
        return {'outbound_rpc_requests': self.count, 'methods': dict(self.methods),
                'estimated_cost_usd': self.count * 6 / 1_000_000,
                'cumulative_ledger_estimate_usd': budget['spent_usd'],
                'prior_unmetered_estimate_now_in_ledger_usd': sum(e['amount_usd'] for e in prior),
                'pricing_source': 'https://drpc.org/docs/pricing/compute-units',
                'billing_confirmed': False, 'proxy_errors': self.errors}


def account_prior_requests(guard, count):
    """Import the recorded pre-metering probe estimate once into the shared cap."""
    if type(count) is not int or count < 0:
        raise ValueError('Prior request count must be a nonnegative integer')
    source = 'pre-metering-drpc-probes-2026-10-15'
    with guard._locked():
        state = guard._read()
        if any(e.get('source') == source for e in state['events']):
            return
        amount = guard._price('drpc-request', count, 0)
        pending = sum(item['reserved_usd'] for item in state['reservations'].values())
        if state['spent_usd'] + pending + amount > guard.limit_usd:
            raise BudgetApprovalRequired('Prior RPC estimate would exceed cumulative paid cap')
        state['spent_usd'] += amount
        state['events'].append({'event': 'external-estimate', 'source': source,
            'estimated_requests': count, 'amount_usd': amount, 'usage_source': 'estimate'})
        guard._write(state)


@contextmanager
def upstream_proxy(meter):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2 * 1024 * 1024:
                    raise ValueError('Invalid RPC request size')
                payload = json.loads(self.rfile.read(size))
                data = meter.forward(payload)
            except Exception as error:
                # Codes and local boundary names only, never upstream exception text.
                kind = type(error).__name__
                meter.errors.append(kind)
                data = {'jsonrpc': '2.0', 'id': None, 'error': {
                    'code': -32099, 'message': 'Metered archive boundary failed: ' + kind}}
            body = json.dumps(data).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except ConnectionError:
                # Anvil's timeout may expire before an upstream read returns.
                meter.errors.append('local-client-disconnected-after-upstream-request')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def local_rpc(url, method, params, timeout_seconds=120):
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 900:
        raise ValueError('Local RPC timeout must be bounded to 1..900 seconds')
    request = Request(url, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
        'method': method, 'params': params}).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            data = json.load(response)
    except TimeoutError:
        raise RuntimeError(f'Local {method} timed out after {timeout_seconds} seconds') from None
    if data.get('error'):
        message = re.sub(r'https?://[^\s\"\'<>]+', '[endpoint]', str(data['error'].get('message','')))
        raise RuntimeError(f'Local {method} failed: RPC code {data["error"].get("code")}: {message[:400]}')
    return data.get('result')


def verify_receipt(expected, actual):
    for field in ['transactionHash', 'status', 'gasUsed', 'transactionIndex', 'contractAddress']:
        if expected.get(field) != actual.get(field):
            raise ValueError('Historical receipt mismatch: ' + field)
    def logs(receipt):
        return [(x['address'].lower(), x['topics'], x['data']) for x in receipt.get('logs', [])]
    if logs(expected) != logs(actual):
        raise ValueError('Historical receipt mismatch: logs')


def validate_storage(opcode, call):
    from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
    from faultseeker.utils.rpc_provider import normalize_trace_node
    root = normalize_trace_node(call)
    normalized = normalize_opcode_storage_trace(opcode['structLogs'], root)
    if not normalized['normalization_complete']:
        raise ValueError('Opcode frame normalization incomplete')
    owners = {}
    def walk(node, inherited=None):
        owner = inherited if node['call_type'] in {'DELEGATECALL', 'CALLCODE'} else node['callee'].lower()
        owners[node['call_id']] = owner
        for child in node['children']:
            walk(child, owner)
    walk(root)
    for entry in normalized['storage_reads'] + normalized['storage_events']:
        if owners.get(entry['call_id']) != entry['address']:
            raise ValueError('Storage owner does not match call frame context')
    for operation, field in [('SLOAD', 'storage_reads'), ('SSTORE', 'storage_events')]:
        if sum(x['op'] == operation for x in opcode['structLogs']) != len(normalized[field]):
            raise ValueError('Storage opcode count mismatch: ' + operation)
    return normalized


def hardfork(block):
    timestamp = int(block['timestamp'], 16)
    if timestamp >= 1746612311:
        raise ValueError('This replay runner is bounded to pre-Pectra blocks')
    if timestamp >= 1710338135:
        return 'cancun'
    if timestamp >= 1681338455:
        return 'shanghai'
    if int(block['number'], 16) >= 15537394:
        return 'paris'
    if int(block['number'], 16) >= 12965000:
        return 'london'
    raise ValueError('This replay runner is bounded to London and later blocks')


def signed_transaction(transaction):
    """Rebuild a signed EIP-2718 envelope, then verify its canonical Keccak hash."""
    import rlp
    from eth_utils import keccak
    def integer(name, default=None):
        value = transaction.get(name, default)
        return int(value, 16) if isinstance(value, str) else int(value)
    def binary(value):
        return bytes.fromhex((value or '').removeprefix('0x'))
    kind = integer('type', 0)
    body = [integer('nonce'), integer('gas'), binary(transaction.get('to')),
            integer('value'), binary(transaction.get('input', transaction.get('data', '0x')))]
    signature = [integer('v'), integer('r'), integer('s')]
    if kind == 0:
        fields = [body[0], integer('gasPrice')] + body[1:] + signature
        raw = rlp.encode(fields)
    elif kind in (1, 2, 3):
        access = [[binary(item['address']), [binary(slot) for slot in item['storageKeys']]]
                  for item in transaction.get('accessList', [])]
        fees = ([integer('gasPrice')] if kind == 1 else
                [integer('maxPriorityFeePerGas'), integer('maxFeePerGas')])
        fields = [integer('chainId'), body[0]] + fees + body[1:] + [access]
        if kind == 3:
            fields += [integer('maxFeePerBlobGas'),
                       [binary(item) for item in transaction['blobVersionedHashes']]]
        raw = bytes([kind]) + rlp.encode(fields + signature)
    else:
        raise ValueError('Unsupported canonical transaction type: ' + str(kind))
    if '0x' + keccak(raw).hex() != transaction['hash'].lower():
        raise ValueError('Reconstructed signed envelope does not match canonical hash')
    return '0x' + raw.hex()


def validate_recorded_capture(path, expected_hash):
    """Recheck preserved replay output without making any network requests."""
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        capture = json.load(handle)
    if (capture['transaction_hash'] != expected_hash or capture['chain'] != 'eth'
            or capture['capture_version'] != 'anvil-historical-v1'):
        raise ValueError('Recorded historical capture identity mismatch')
    receipt = capture['canonical_receipt']
    block = capture['canonical_block']
    index = int(receipt['transactionIndex'], 16)
    prefix = block['transactions'][:index + 1]
    if (receipt['transactionHash'] != expected_hash or receipt['blockHash'] != block['hash']
            or prefix[-1]['hash'] != expected_hash
            or capture['fork_parent_block'] != int(block['number'], 16) - 1
            or [tx['hash'] for tx in prefix] != capture['replayed_prefix_hashes']):
        raise ValueError('Recorded canonical block prefix mismatch')
    for tx in prefix:
        signed_transaction(tx)
    verify_receipt(receipt, capture['replay_receipt'])
    storage = validate_storage(capture['raw_trace']['opcode'], capture['raw_trace']['call'])
    if storage != capture['normalization']:
        raise ValueError('Stored normalization differs from raw opcode reconstruction')
    return {'transaction_hash': expected_hash, 'sload_count': len(storage['storage_reads']),
            'sstore_count': len(storage['storage_events']), 'storage_owners_verified': True,
            'artifact_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def replay_one(tx_hash, label, meter, proxy_url, anvil, output, mine_timeout=120):
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', tx_hash):
        raise ValueError('Invalid transaction hash')
    transaction = meter.rpc('eth_getTransactionByHash', [tx_hash])
    receipt = meter.rpc('eth_getTransactionReceipt', [tx_hash])
    block = meter.rpc('eth_getBlockByHash', [receipt['blockHash'], True])
    index = int(receipt['transactionIndex'], 16)
    if (transaction['blockHash'] != block['hash'] or receipt['transactionHash'] != tx_hash
            or block['transactions'][index]['hash'] != tx_hash):
        raise ValueError('Canonical transaction/block identity mismatch')
    parent = int(block['number'], 16) - 1
    prefix = block['transactions'][:index + 1]
    signed = [signed_transaction(tx) for tx in prefix]
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    arguments = [anvil, '--host', '127.0.0.1', '--port', str(port), '--silent',
        '--accounts', '0', '--fork-url', proxy_url, '--fork-block-number', str(parent),
        '--chain-id', '1', '--hardfork', hardfork(block), '--steps-tracing',
        '--no-mining', '--order', 'fifo', '--no-storage-caching', '--no-fork-node-info',
        '--no-bal', '--retries', '0', '--timeout', '45000', '--gas-limit', str(int(block['gasLimit'], 16))]
    process = subprocess.Popen(arguments, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError('Anvil exited during archive fork startup')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError('Anvil fork startup timed out (20 seconds)')
        fork = local_rpc(url, 'eth_getBlockByNumber', [hex(parent), False])
        if not fork or fork['hash'] != block['parentHash']:
            raise ValueError('Fork parent hash mismatch')
        local_rpc(url, 'evm_setNextBlockTimestamp', [int(block['timestamp'], 16)])
        local_rpc(url, 'anvil_setNextBlockBaseFeePerGas', [block['baseFeePerGas']])
        local_rpc(url, 'anvil_setCoinbase', [block['miner']])
        if hardfork(block) != 'london':
            local_rpc(url, 'anvil_setNextBlockPrevRandao', [block['mixHash']])
        if block.get('parentBeaconBlockRoot'):
            local_rpc(url, 'anvil_setNextBlockParentBeaconBlockRoot', [block['parentBeaconBlockRoot']])
        for tx, raw in zip(prefix, signed):
            accepted = local_rpc(url, 'eth_sendRawTransaction', [raw])
            if accepted != tx['hash']:
                raise ValueError('Signed replay changed transaction identity')
        local_rpc(url, 'evm_mine', [], timeout_seconds=mine_timeout)
        local_receipt = local_rpc(url, 'eth_getTransactionReceipt', [tx_hash])
        if not local_receipt:
            raise ValueError('Target transaction was not mined in canonical prefix order')
        verify_receipt(receipt, local_receipt)
        local_block = local_rpc(url, 'eth_getBlockByNumber', [block['number'], False])
        if local_block['transactions'] != [tx['hash'] for tx in prefix]:
            raise ValueError('Replayed block prefix differs from canonical order')
        for field in ['number', 'timestamp', 'baseFeePerGas', 'miner', 'gasLimit', 'mixHash']:
            if local_block.get(field) != block.get(field):
                raise ValueError('Historical block environment mismatch: ' + field)
        call = local_rpc(url, 'debug_traceTransaction', [tx_hash, {'tracer': 'callTracer'}])
        opcode = local_rpc(url, 'debug_traceTransaction', [tx_hash, {
            'disableStack': False, 'disableMemory': True, 'disableStorage': False}])
        if not isinstance(opcode, dict) or not opcode.get('structLogs') or opcode.get('failed'):
            raise ValueError('Historical opcode capture is empty or failed')
        storage = validate_storage(opcode, call)
        name = tx_hash + '.json.gz'
        artifact = {'transaction_hash': tx_hash, 'chain': 'eth', 'label': label,
            'transaction': transaction, 'canonical_receipt': receipt, 'replay_receipt': local_receipt,
            'canonical_block': block, 'replayed_prefix_hashes': [tx['hash'] for tx in prefix],
            'fork_parent_block': parent, 'raw_trace': {'call': call, 'opcode': opcode},
            'normalization': storage, 'capture_version': 'anvil-historical-v1'}
        output.mkdir(parents=True, exist_ok=True)
        with gzip.open(output / name, 'wt', encoding='utf-8') as handle:
            json.dump(artifact, handle)
        return {'transaction_hash': tx_hash, 'label': label, 'block': int(block['number'], 16),
            'transaction_index': index, 'prefix_transactions_replayed': len(prefix), 'artifact': name,
            'artifact_sha256': hashlib.sha256((output / name).read_bytes()).hexdigest(),
            'opcode_count': len(opcode['structLogs']), 'sload_count': len(storage['storage_reads']),
            'sstore_count': len(storage['storage_events']), 'normalization_complete': True,
            'storage_owners_verified': True, 'receipt_matches': True,
            'storage_contracts': sorted({e['address'] for e in storage['storage_reads'] + storage['storage_events']})}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stderr:
            # Its upstream URL is localhost, but do not publish arbitrary process output.
            process.stderr.close()


def run(output, transaction_hashes=None, max_requests=5000, mine_timeout=120):
    values = dotenv_values(ROOT / '.env')
    endpoint = os.getenv('DRPC_RPC_URL') or values.get('DRPC_RPC_URL') or ''
    key = os.getenv('DRPC_API_KEY') or values.get('DRPC_API_KEY') or ''
    endpoint = endpoint.replace('{chain}', 'eth').replace('{api_key}', quote(key, safe=''))
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or not (
            parsed.hostname == 'drpc.org' or parsed.hostname.endswith('.drpc.org')
            or parsed.hostname == 'drpc.live' or parsed.hostname.endswith('.drpc.live')):
        raise ValueError('DRPC_RPC_URL must be an HTTPS dRPC endpoint')
    anvil = os.getenv('ANVIL_BINARY') or shutil.which('anvil') or str(ROOT / 'build/tools/anvil.exe')
    if not Path(anvil).is_file():
        raise ValueError('ANVIL_BINARY missing')
    output = Path(output)
    # Unit/integration tests isolate this ledger through the existing fixture.
    meter = MeteredRPC(endpoint, os.getenv('FAULTSEEKER_SPEND_LEDGER') or ROOT / 'data/research/spend_ledger.json',
                       max_requests=max_requests)
    prior = ROOT / 'reports/live_verification/session_summary.json'
    if prior.is_file():
        account_prior_requests(meter.guard,
            json.loads(prior.read_text(encoding='utf-8'))['drpc']['outbound_rpc_requests'])
    report = {'status': 'BLOCKED', 'cases': [], 'scope': 'historical opcode capture, not incident adjudication'}
    try:
        if meter.rpc('eth_chainId', []) != '0x1':
            raise ValueError('Endpoint is not Ethereum mainnet')
        with (ROOT / 'benchmark/benchmark_classification_fixed.csv').open(encoding='utf-8-sig') as handle:
            rows = {r['txn_hash']: r for r in csv.DictReader(handle) if r['chain'] == 'eth'}
        with upstream_proxy(meter) as proxy:
            for tx in transaction_hashes or [REENTRANT, COMPARISON]:
                report['current_transaction'] = tx
                if tx not in rows:
                    raise ValueError('Transaction is not an Ethereum row in benchmark_classification_fixed.csv')
                label = ('labeled reentrant in benchmark_classification_fixed.csv'
                         if 'reentran' in rows[tx]['vuln_type'].lower()
                         else 'not labeled reentrant in benchmark_classification_fixed.csv')
                case = replay_one(tx, label, meter, proxy, anvil, output, mine_timeout=mine_timeout)
                report['cases'].append(case)
                print(json.dumps({'captured': tx, 'sloads': case['sload_count'],
                                  'sstores': case['sstore_count']}), flush=True)
        report['status'] = 'CAPTURED'
    except Exception as error:
        # Exceptions from urlopen may contain the secret-bearing URL.
        message = str(error).replace(endpoint, '[RPC_URL]')
        if key:
            message = message.replace(key, '[REDACTED]')
        report['failure'] = {'type': type(error).__name__, 'reason': message[:1000]}
    finally:
        report['rpc_usage'] = meter.summary()
        write_json(output / 'historical_replay_summary.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/historical_replay')
    parser.add_argument('--max-requests', type=int, default=5000)
    parser.add_argument('--transaction', action='append')
    parser.add_argument('--mine-timeout', type=int, default=120)
    args = parser.parse_args()
    if not args.execute_live:
        print('No requests dispatched. Pass --execute-live for counted archive replay.')
        return 2
    result = run(args.output, args.transaction, args.max_requests, args.mine_timeout)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'CAPTURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
