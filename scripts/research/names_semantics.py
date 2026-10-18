"""Lexical saved function identifiers, never verified selector evidence."""
import re
from collections import defaultdict
from faultseeker.function_analysis.candidate_generation import parse_saved_trace_candidates

NUMERIC = ('best_reciprocal', 'reciprocal_sum', 'structural', 'terminal_fanout', 'delegate_neighbor')


def tokens(value):
    text = str(value or '').strip()
    match = re.fullmatch(r'([A-Za-z_$][A-Za-z0-9_$]*)(?:\([^\n]*\))?(?:\s*\{[^{}]*\})?', text)
    if not match or text.lower().startswith('0x'):
        return []
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', match[1])
    name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', name)
    return re.findall(r'[a-z]{2,}', name.lower())


def documents(addresses, predictions, trace_text):
    """Address values join evidence only; never emit them into feature text."""
    collected = defaultdict(list)
    for item in predictions:
        address = str(item.get('code_address') or item.get('address') or '').lower()
        collected[address].extend(tokens(item.get('function_name') or item.get('function')))
    for call in parse_saved_trace_candidates(trace_text):
        collected[call['address']].extend(tokens(call.get('function')))
    return [' '.join(collected[a]) for a in addresses]
