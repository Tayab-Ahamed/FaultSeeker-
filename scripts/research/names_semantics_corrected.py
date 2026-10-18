"""Conservative lexical adapter excluding bare and prefixed selectors."""
import re
from collections import defaultdict
from scripts.research.names_semantics import tokens as original_tokens, NUMERIC
from faultseeker.function_analysis.candidate_generation import parse_saved_trace_candidates


def tokens(value):
    identifier = str(value or '').strip().split('(', 1)[0].split('{', 1)[0].strip()
    if re.fullmatch(r'[0-9a-fA-F]{8}', identifier):
        return []
    return original_tokens(value)


def documents(addresses, predictions, trace_text):
    collected = defaultdict(list)
    for item in predictions:
        address = str(item.get('code_address') or item.get('address') or '').lower()
        collected[address].extend(tokens(item.get('function_name') or item.get('function')))
    for call in parse_saved_trace_candidates(trace_text):
        collected[call['address']].extend(tokens(call.get('function')))
    return [' '.join(collected[a]) for a in addresses]
