"""Execute detector ablations on identical captured call/opcode traces."""
import hashlib
import json
import time
from collections import Counter
from faultseeker.forensics.signal_extractor import SignalExtractor
from faultseeker.data_collection.storage_trace import normalize_opcode_storage_trace
from faultseeker.utils.rpc_provider import normalize_trace_node


def _trace(capture):
    raw = capture['raw_trace']
    if not isinstance(raw, dict) or not isinstance(raw.get('call'), dict):
        raise ValueError('captured call trace required')
    return raw, normalize_trace_node(raw['call'])


def _walk(root):
    yield root
    for child in root.get('children', []):
        yield from _walk(child)


def detector_observation(capture, variant):
    started = time.perf_counter()
    raw, root = _trace(capture)
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    if variant == 'repeated':
        appearances = Counter(node['callee']
                              for node in _walk(root) if node['call_type'] != 'STATICCALL')
        prediction = any(count > 1 for count in appearances.values())
        detail = {'repeated_addresses': sum(count > 1 for count in appearances.values())}
    elif variant in {'full', 'structural'}:
        if variant == 'full':
            opcode = raw.get('opcode')
            if not isinstance(opcode, dict) or not isinstance(opcode.get('structLogs'), list):
                raise ValueError('full detector requires captured opcode logs')
            storage = normalize_opcode_storage_trace(opcode['structLogs'], root)
            if not storage['normalization_complete']:
                raise ValueError('Full detector measurement requires complete opcode normalization')
        else:
            storage = {'storage_events': [], 'storage_reads': []}
        analysis = dict(storage, canonical_trace=root, trace={}, flatten_trace=[], repeated_patterns={})
        signals = SignalExtractor(txn_seq={'trace_coverage':{'storage_trace_complete':variant=='full'}},
                                  tx_analysis=analysis, paper_mode=True).run()
        detail = signals.raw['reentrancy']
        # Paper IV-B: only HIGH_RISK and CONFIRMED are metric positives.
        # The engine's broader POSSIBLE alert threshold is unchanged.
        prediction = detail['tier'] in {'HIGH_RISK_REENTRANCY', 'CONFIRMED_REENTRANCY'}
    else:
        raise ValueError('Unknown detector variant')
    return {'predicted_exploit': bool(prediction), 'algorithm': variant,
            'input_sha256': digest, 'detector_result': detail,
            'ranked_functions': [], 'query_records': [],
            'duration_seconds': time.perf_counter()-started}


def category_observation(capture, receipt, category):
    _, root = _trace(capture)
    nodes = list(_walk(root))
    gas = receipt['gasUsed']
    gas = int(gas,16) if isinstance(gas,str) and gas.startswith('0x') else int(gas)
    if gas < 0:
        raise ValueError('negative receipt gas')
    addresses = {address for node in nodes for address in (node.get('caller'),node.get('callee')) if address}
    return {'category':category,'gas_used':gas,'function_calls':len(nodes),
            'addresses':len(addresses),'max_depth':max(node['depth'] for node in nodes)}
