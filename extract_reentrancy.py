import csv
import json
import os
import sys

# ensure module resolution
_HERE = os.getcwd()
sys.path.insert(0, _HERE)

from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from benchmark.run_eval import get_expected_signals, normalize_signals

rows = []
with open('benchmark/benchmark_classification_fixed.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        # We only want ETH right now because BSC public RPC is timing out
        if 'Reentrancy' in row.get('dasp_classification', '') and row.get('chain', '').lower() == 'eth':
            # Also mock the dict for get_expected_signals
            r = dict(row)
            r['dasp'] = r.pop('dasp_classification', '')
            r['swc'] = r.pop('swc_registry_classification', '')
            rows.append(r)

print(f"Found {len(rows)} Reentrancy transactions on ETH. Will test first 5...")

orch = ForensicsOrchestrator()
for idx, r in enumerate(rows[:5]):
    print(f"\n=======================================================")
    print(f"--- [Reentrancy {idx+1}/5] TX: {r['txn_hash']} ---")
    print(f"=======================================================")
    try:
        forensics_result, _, _ = orch.run(r['txn_hash'], 'eth')
        if not forensics_result:
            print("Failed to get trace (None returned)")
            continue
            
        raw_signals = forensics_result.signals.raw
        pred = normalize_signals(raw_signals)
        expected = get_expected_signals(r)
        
        print("Expected Signals:", list(expected))
        print("Predicted Reentrancy:", pred.get("reentrancy_detected", False))
        print("Raw Reentrancy Score:", raw_signals.get("reentrancy_score"))
        
        if pred.get("reentrancy_detected") == ("reentrancy_detected" in expected):
            print("-> [CORRECT]")
        else:
            print("-> [FAILURE]")
            print("Raw signals:")
            print(json.dumps(raw_signals, indent=2))
            
    except Exception as e:
        print("Failed to evaluate:", getattr(e, 'message', str(e)))
