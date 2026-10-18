"""Pure saved-evidence candidate coverage adapter; no labels or I/O."""
from __future__ import annotations
import re
from scripts.research import address_ranking_phase1 as base
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions
from faultseeker.function_analysis.candidate_generation import parse_saved_trace_candidates

ALLOWED = ('code_address', 'address', 'function', 'function_name', 'count', 'supporting_call_depths')
ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}(?![0-9a-fA-F])')
FEATURES = ('baseline_reciprocal', 'baseline_sum', 'baseline_structural', 'baseline_fanout',
            'trace_calls', 'trace_depth', 'trace_delegate', 'trace_static',
            'trace_references', 'trace_event_references')


def extract_candidates(predictions, trace_text):
    clean = [{k: p[k] for k in ALLOWED if k in p} for p in predictions]
    evidence = base.extract_evidence(rerank_saved_predictions(clean), trace_text)
    candidates = {}
    def ensure(address):
        address = str(address).lower()
        if not ADDRESS.fullmatch(address) or address == '0x' + '0'*40:
            return None
        if address not in candidates:
            candidates[address] = dict(address=address, **{f: 0. for f in FEATURES})
        return candidates[address]
    for item in evidence:
        row = ensure(item['address'])
        if row is not None:
            for src, dst in [('best_reciprocal','baseline_reciprocal'), ('reciprocal_sum','baseline_sum'),
                             ('structural','baseline_structural'), ('terminal_fanout','baseline_fanout')]:
                row[dst] = item[src]
    calls = parse_saved_trace_candidates(trace_text)
    for call in calls:
        row = ensure(call['address'])
        if row is None:
            continue
        row['trace_calls'] += 1
        row['trace_depth'] = max(row['trace_depth'], call['depth'])
        row['trace_delegate'] += call['call_type'] == 'delegatecall'
        row['trace_static'] += call['call_type'] == 'staticcall'
        if call.get('proxy_address'):
            proxy = ensure(call['proxy_address'])
            if proxy is not None:
                proxy['trace_delegate'] += 1
    for line in str(trace_text or '').splitlines():
        # Only trace call or event lines: exclude warnings, hashes and arbitrary logs.
        if not ('::' in line or re.search(r'\bemit\s+\w+\(', line)):
            continue
        for address in ADDRESS.findall(line):
            row = ensure(address)
            if row is not None:
                row['trace_references'] += 1
                row['trace_event_references'] += bool(re.search(r'\bemit\s+', line))
    for feature in FEATURES:
        if feature.startswith('trace_'):
            maximum = max((r[feature] for r in candidates.values()), default=0)
            if maximum:
                for row in candidates.values():
                    row[feature] /= maximum
    return list(candidates.values())


def rank_candidates(evidence, config):
    if config['kind'] == 'call_append':
        return [r['address'] for r in evidence if r['baseline_reciprocal'] or r['trace_calls'] or r['trace_delegate']]
    if config['kind'] == 'reference_append':
        return [r['address'] for r in evidence]
    def score(row):
        return (row['baseline_reciprocal'] + config['calls']*row['trace_calls']
                + config['delegate']*row['trace_delegate'] + config['references']*row['trace_references'])
    return [r['address'] for _, r in sorted(enumerate(evidence), key=lambda p: (-score(p[1]), p[0]))]
