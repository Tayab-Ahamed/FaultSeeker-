"""Hash-bound historical inputs for production forensics; no outcome substitutes.

Only I/O collectors are replaced by recorded-input readers. The sequencer,
trace analyzer, signal extractor, rule classifier, address classifier and fund
flow analyzer are the actual production implementations. No labels reach them.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
from benchmark.research_protocol import admit, identity, load_train, read_bound, sha
from faultseeker.data_collection.txn_sequencer import TransactionSequencer
from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector
from faultseeker.utils.rpc_provider import normalize_trace_node
from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
from scripts.capture_authentic_traces import validate_call_identity
from scripts.replay_historical_opcodes import validate_recorded_capture

BASE = Path('reports/cohort_rebuild_v2')


class _CapturedSequencer(TransactionSequencer):
    def __init__(self, structured):
        super().__init__()
        self.structured = structured

    def run(self, txn_hash, chain):
        if txn_hash != self.structured['transaction_hash'] or chain != self.structured['chain']:
            raise ValueError('Recorded sequence identity mismatch')
        return self.from_structured(deepcopy(self.structured))


class _CapturedInfo:
    def __init__(self, tx, receipt, txn_hash, chain):
        self.tx, self.receipt, self.txn_hash, self.chain = tx, receipt, txn_hash, chain

    def run(self, txn_hash, chain):
        if txn_hash != self.txn_hash or chain != self.chain:
            raise ValueError('Recorded RPC identity mismatch')
        info = TransactionInfoCollector.from_rpc(self.tx, self.receipt, txn_hash)
        if not info:
            raise ValueError('Recorded RPC normalization failed')
        info['_source'] = 'hash-bound captured transaction and canonical receipt'
        return deepcopy(info)


class CapturedInputs:
    def __init__(self, row, binding, root, require_opcodes):
        if not admit(row, root)['accepted']:
            raise ValueError('Captured input admission invalid')
        raw = read_bound(binding, root)
        capture = json.loads(gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw)
        rpc = json.loads(read_bound(row['rpc'], root))
        if capture.get('transaction_hash') != row['txn_hash'] or capture.get('chain') != row['chain']:
            raise ValueError('Captured execution identity mismatch')
        validate_call_identity(capture['raw_trace']['call'], rpc['transaction'], rpc['receipt'])
        full = isinstance(capture['raw_trace'].get('opcode', {}).get('structLogs'), list)
        if require_opcodes and not full:
            raise ValueError('Complete opcode capture required for this experiment')
        self.proof = validate_recorded_capture(root / binding['path'], row['txn_hash'], root) if full else None
        canonical = normalize_trace_node(capture['raw_trace']['call'])
        storage = normalize_opcode_storage_trace(capture['raw_trace']['opcode']['structLogs'], canonical) if full else {}
        self.structured = {'transaction_hash': row['txn_hash'], 'chain': row['chain'], 'trace': canonical,
            'storage_events': storage.get('storage_events', []), 'storage_reads': storage.get('storage_reads', []),
            'state_diff': {}, 'trace_coverage': {
                'trace_complete': full, 'storage_trace_complete': full,
                'token_flow_complete': False, 'multi_tx_context_complete': False}}
        self.rpc = rpc
        self.evidence = {'rpc': row['rpc'], 'capture': binding, 'admission': 'source-adjudicated frozen train row'}

    def orchestrator(self, cache_dir):
        from faultseeker.forensics.orchestrator import ForensicsOrchestrator
        return ForensicsOrchestrator(cache_dir=str(cache_dir),
            txn_sequencer=_CapturedSequencer(self.structured),
            txn_info_collector=_CapturedInfo(self.rpc['transaction'], self.rpc['receipt'],
                self.structured['transaction_hash'], self.structured['chain']))


def load_train_inputs(root, requested_identity, require_opcodes=True):
    root = Path(root).resolve()
    split = json.loads((root / 'benchmark/eval_split.json').read_text())
    if sha((root / 'benchmark/cohort_manifest.json').read_bytes()) != split['manifest_sha256']:
        raise ValueError('Frozen manifest digest mismatch')
    if requested_identity not in split['train_ids']:
        raise ValueError('Requested identity is outside frozen train')
    rows = load_train(split, root)
    row = next(r for r in rows if identity(r) == requested_identity)
    binding = None
    for filename in ('opcode_acquisition_train.json', 'trace_acquisition_train.json'):
        path = root / BASE / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        records = data.get('attempts', []) if isinstance(data, dict) else data
        if any(r['identity'] not in split['train_ids'] for r in records):
            raise ValueError('Non-train identity in acquisition index')
        selected = next((r for r in records if r['identity'] == requested_identity and r.get('artifact')), None)
        if selected:
            binding = selected['artifact']
            break
    binding = binding or row.get('trace')
    if not binding:
        raise ValueError('No recorded trace for train identity')
    return CapturedInputs(row, binding, root, require_opcodes)
