import sys, os, json

_HERE = os.getcwd()
sys.path.insert(0, _HERE)

from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from benchmark.run_eval import get_expected_signals, normalize_signals

DATASET_DIR = "data/dataset/reentrancy/"
os.makedirs(DATASET_DIR, exist_ok=True)

# 1. Grab 1 specific Reentrancy Hash from the ETH dataset
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

def save_to_dataset(tx_hash, raw_signals, trace_data):
    path = os.path.join(DATASET_DIR, f"{tx_hash}.json")
    with open(path, 'w') as f:
        json.dump({"signals": raw_signals, "trace": trace_data}, f, indent=2)

orch = ForensicsOrchestrator()

try:
    res, trace_data, _ = orch.run(target_tx, 'eth')
    
    if res is None:
        raise RuntimeError(f"Trace fetch failed for {target_tx}. Archive Trace endpoint is missing or rate limited.")
        
    raw = res.signals.raw if hasattr(res.signals, 'raw') else res.signals
    if hasattr(raw, 'get'):
        pass
    else:
        raw = vars(raw)
        
    save_to_dataset(target_tx, raw, trace_data)
    
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
    
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[FAIL-FAST] {e}")
    sys.exit(1)
