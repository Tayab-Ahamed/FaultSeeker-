import sys, os, json

_HERE = os.getcwd()
sys.path.insert(0, _HERE)

from faultseeker.forensics.signal_extractor import SignalExtractor
from benchmark.run_eval import normalize_signals, get_expected_signals

# 1. Grab target specific Reentrancy Hash from the ETH dataset
target_tx = "0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6"

def get_expected(tx_hash):
    import csv
    with open('benchmark/benchmark_classification_fixed.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['txn_hash'].strip() == tx_hash:
                r = dict(row)
                r['dasp'] = r.pop('dasp_classification', '')
                r['swc'] = r.pop('swc_registry_classification', '')
                return list(get_expected_signals(r))
    return []

try:
    print(f"====================================")
    print(f" Evaluating LOCAL OFFLINE Reentrancy: {target_tx}")

    trace_data = json.load(open("data/dataset/reentrancy/test1.json"))
    
    # Normally Orchestrator builds tx_analysis. We map the raw JSON payload structurally here.
    # We will assume it's roughly shaped like tx_analysis for this test, or we run the parsers
    # on it depending on the source structure. If it's a Tenderly/raw JSON-RPC trace, 
    # we need to ensure the format aligns with what `SignalExtractor` expects.
    
    # Actually, orchestrator's trace fallback maps it! Let's simulate orchestrator state 
    # if it bypassed cast and loaded this. 
    # Assuming 'test1.json' is a direct drop-in of ForensicsResult signals or tx_analysis.
    
    # Since we need to test the heuristic logic, we'll pass it directly if it matches.
    # To keep it completely isolated:
    extractor = SignalExtractor({}, trace_data.get('tx_analysis', trace_data), target_tx, 'eth')
    res = extractor.run()
    raw = res.raw

    pred = normalize_signals(raw)
    
    print("\n--- REENTRANCY DEBUG ---")
    print("TX:", target_tx)
    print("Expected:", get_expected(target_tx))
    print("Predicted:", pred.get("reentrancy_detected", False))
            
    print("\n--- INTERNAL TRACE FEATURES ---")
    debug_map = raw.get('debug', {})
    if not debug_map:
        print("[!] Warning: Instrumentation silent (debug not found)")
    else:
        for k, v in debug_map.items():
            if k != 'score_components':
                print(f"{k}: {v}")
                
    print("\n--- SCORE BREAKDOWN ---")
    if 'score_components' in debug_map:
        for k, v in debug_map['score_components'].items():
            print(f"{k}: {v}")
        
    print(f"\nreentrancy_score: {raw.get('reentrancy_score', 0)}")
    print("threshold: 5")
    print(f"reentrancy_detected: {pred.get('reentrancy_detected', False)}")
    
except FileNotFoundError:
    print("\n[!] 'data/dataset/reentrancy/test1.json' not found.")
    print("Please export the trace from Tenderly and save it to this path.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[FAIL-FAST] {e}")
