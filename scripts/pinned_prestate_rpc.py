"""Read-through parent-state cache for first-in-block, pre-Shanghai Ethereum txs.

The non-diff prestate is an actual RPC artifact, not a synthetic state override.
For transaction index zero before Shanghai, its observed initial account fields
are parent-block state: there are no earlier transactions or withdrawal/beacon
system transitions to account for. We cache only explicit fields and slots, for
an exact parent block tag. Every miss uses the original metered archive endpoint.
Canonical signed transaction, receipt and environment checks remain mandatory.
"""
from collections import Counter
import gzip
import json
import re
import threading
from benchmark.research_protocol import read_bound

ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}\Z')


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not an RPC integer')
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and re.fullmatch(r'0x[0-9a-fA-F]+', value):
        result = int(value, 16)
    else:
        raise ValueError('Invalid RPC integer')
    if result < 0 or result >= 2**256:
        raise ValueError('RPC integer is outside uint256')
    return result


class PinnedPrestateRPC:
    def __init__(self, upstream, row, root):
        self.upstream = upstream
        self.row = row
        self.source = row['prestate']
        record = json.loads(gzip.decompress(read_bound(self.source, root)))
        rpc = json.loads(read_bound(row['rpc'], root))
        self.receipt = rpc['receipt']
        if (row['chain'] != 'eth' or rpc['chain_id'] != 1
                or number(self.receipt['transactionIndex']) != 0):
            raise ValueError('Parent prestate cache requires Ethereum first transaction in block')
        params = record.get('request', {}).get('params', [])
        if (record.get('transaction_hash') != row['txn_hash'] or record.get('chain') != 'eth'
                or self.receipt.get('transactionHash') != row['txn_hash']
                or rpc.get('transaction', {}).get('hash') != row['txn_hash']
                or record.get('request', {}).get('method') != 'debug_traceTransaction'
                or len(params) != 2 or params[0] != row['txn_hash']
                or params[1].get('tracer') != 'prestateTracer'
                or params[1].get('tracerConfig') != {'diffMode': False, 'disableCode': False, 'disableStorage': False}
                or record.get('response', {}).get('error')):
            raise ValueError('Prestate RPC identity/config mismatch')
        if record.get('rpc_identity') is not None and record['rpc_identity'] != row['rpc']:
            raise ValueError('Prestate source has different RPC identity evidence')
        self.accounts = record['response'].get('result')
        if (not isinstance(self.accounts, dict) or not self.accounts
                or any(not ADDRESS.fullmatch(a) or not isinstance(v, dict) for a,v in self.accounts.items())):
            raise ValueError('Non-diff prestate accounts required')
        self.accounts = {a.lower(): v for a,v in self.accounts.items()}
        self.parent = number(self.receipt['blockNumber']) - 1
        self.active = False
        self.parent_hash = None
        self.hits = Counter()
        self.lock = threading.Lock()

    @property
    def count(self):
        return self.upstream.count

    @property
    def max_requests(self):
        return self.upstream.max_requests

    @property
    def errors(self):
        return self.upstream.errors

    def activate(self, block, transaction_hash):
        if (transaction_hash != self.row['txn_hash'] or block['hash'] != self.receipt['blockHash']
                or number(block['number']) != self.parent + 1
                or not block.get('transactions') or block['transactions'][0]['hash'] != transaction_hash):
            raise ValueError('Prestate canonical block identity mismatch')
        if number(block['timestamp']) >= 1681338455:
            raise ValueError('Parent prestate cache is restricted to pre-Shanghai blocks')
        self.parent_hash = block['parentHash']
        self.active = True

    def _lookup(self, payload):
        if not self.active or not isinstance(payload, dict):
            return None
        method, params = payload.get('method'), payload.get('params')
        sizes = {'eth_getBalance': 2, 'eth_getCode': 2, 'eth_getTransactionCount': 2, 'eth_getStorageAt': 3}
        if method not in sizes or not isinstance(params, list) or len(params) != sizes[method]:
            return None
        try:
            # EIP-1898 hash tags must match the canonical parent exactly.
            tag = params[-1]
            if isinstance(tag, dict):
                if (set(tag) <= {'blockHash', 'requireCanonical'} and 'blockHash' in tag
                        and type(tag.get('requireCanonical', False)) is bool):
                    matched = tag['blockHash'] == self.parent_hash
                elif set(tag) == {'blockNumber'}:
                    matched = number(tag['blockNumber']) == self.parent
                else:
                    matched = False
            else:
                matched = isinstance(tag, str) and number(tag) == self.parent
            if not matched:
                return None
            if not isinstance(params[0], str) or not ADDRESS.fullmatch(params[0]):
                return None
            account = self.accounts.get(params[0].lower(), {})
            if method == 'eth_getStorageAt':
                slot = number(params[1])
                storage = account.get('storage', {})
                observed = next((value for key,value in storage.items() if number(key) == slot), None)
                if observed is None:
                    return None
                result = '0x' + format(number(observed), '064x')
            elif method == 'eth_getCode':
                result = account.get('code')
                if not isinstance(result, str) or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', result):
                    return None
            else:
                field = 'balance' if method == 'eth_getBalance' else 'nonce'
                if field not in account:
                    return None
                result = hex(number(account[field]))
        except (ValueError, TypeError, AttributeError):
            return None
        with self.lock:
            self.hits[method] += 1
        return {'jsonrpc': '2.0', 'id': payload.get('id'), 'result': result}

    def forward(self, payload):
        if isinstance(payload, list):
            # Preserve request IDs and ordering; every cache miss is still metered.
            return [self.forward(call) for call in payload]
        cached = self._lookup(payload)
        return cached if cached is not None else self.upstream.forward(payload)

    def rpc(self, method, params):
        data = self.forward({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        if data.get('error') or data.get('result') is None:
            raise RuntimeError(f'{method} failed (RPC code {data.get("error", {}).get("code")})')
        return data['result']

    def cache_evidence(self):
        return {'mode': 'observed-prestate-exact-parent-read-cache-v1', 'prestate': self.source,
                'rpc_identity': self.row['rpc'], 'transaction_hash': self.row['txn_hash'],
                'parent_block': self.parent, 'first_in_block': True, 'pre_shanghai_only': True,
                'cache_hits': sum(self.hits.values()), 'methods': dict(self.hits),
                'unknown_fields_and_slots': 'metered upstream fallback; never defaulted to zero'}

    def summary(self):
        return dict(self.upstream.summary(), prestate_read_cache=self.cache_evidence())
