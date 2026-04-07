import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from dotenv import load_dotenv
load_dotenv()

from faultseeker.utils.rpc_provider import (
    probe_trace_support, _http_post, _check_rpc_error,
    _PROBE_TXS, normalize_trace_node
)

print("Testing trace capability on ETH providers (force re-probe)...")
result = probe_trace_support('eth', force=True)

if not result:
    print("\nTRACE FAILED — No provider supports debug_traceTransaction")
    print("\nTo fix this, add ONE of these to .env:")
    print("  TENDERLY_RPC_URL=https://mainnet.gateway.tenderly.co/... (Dashboard -> Web3 Gateway -> HTTP)")
    print("  ETH_RPC_URL=https://rpc.ankr.com/eth/your_ankr_key")
    sys.exit(1)

# Detailed trace inspection on working provider
print(f"\nTRACE OK — provider: {result}")
print("\nRunning detailed trace inspection...")

def _walk(node, depth=0):
    """Walk a normalized trace node, collecting depth, call count, and types."""
    children = node.get('children', [])
    ct = node.get('call_type', 'CALL')
    max_d = depth
    count = 1
    types = {ct}
    for child in children:
        _, cd, cc, ct_set = _walk(child, depth + 1)
        max_d = max(max_d, cd)
        count += cc
        types |= ct_set
    return True, max_d, count, types

test_tx = _PROBE_TXS['eth'][0]
body = json.dumps({
    'jsonrpc': '2.0', 'method': 'debug_traceTransaction',
    'params': [test_tx, {'tracer': 'callTracer', 'timeout': '8s'}],
    'id': 1,
}).encode()

try:
    data  = _http_post(result, body, timeout=10)
    raw   = _check_rpc_error(data)
    norm  = normalize_trace_node(raw or {})
    _, max_depth, call_count, call_types = _walk(norm)
    has_dc = 'DELEGATECALL' in call_types

    print(f"  tx:             {test_tx[:20]}...")
    print(f"  calls:          {call_count}")
    print(f"  depth:          {max_depth}")
    print(f"  delegatecall:   {has_dc}")
    print(f"  types:          {', '.join(sorted(call_types))}")

    if call_count > 1 and max_depth > 0:
        print("\n[READY] Internal call graph visible. Heuristics will work correctly.")
    else:
        print("\n[WARN] Trace appears shallow — provider may be flattening internal calls.")
except Exception as e:
    print(f"\n[ERROR] Detailed inspection failed: {e}")

