import csv
import json
import glob
import os
import sys

# ensure module resolution
_HERE = os.getcwd()
sys.path.insert(0, _HERE)

from faultseeker.forensics.signal_extractor import SignalExtractor
from benchmark.run_eval import get_expected_signals, normalize_signals

rows = {}
with open('benchmark/benchmark_classification_fixed.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        r = dict(row)
        r['dasp'] = r.pop('dasp_classification', '')
        r['swc'] = r.pop('swc_registry_classification', '')
        rows[r['txn_hash'].strip()] = r

found_any = False
for f in glob.glob('data/cache/forensics/*.json'):
    txn = os.path.basename(f).replace('.json', '')
    if txn not in rows:
        continue
    r = rows[txn]
    
    # We want adversarial cases: Reentrancy
    if 'Reentrancy' not in r['dasp']:
        continue
        
    found_any = True
    print(f"\n=======================================================")
    print(f"--- [REENTRANCY] TX: {txn} ---")
    data = json.load(open(f))
    internal = data.get('_internal', {})
    
    tx_analysis = {
        'flatten_trace':     internal.get('flatten_trace', []),
        'trace':             internal.get('trace', {}),
        'function_call_loc_memo': internal.get('function_call_loc_memo', {}),
        'function_calls_to_expand_loc': internal.get('function_calls_to_expand_loc', {}),
        'repeated_patterns': data.get('function_analysis', {}).get('repeated_patterns', {}),
        'address_calls_with_created_contract_in_params':
            data.get('function_analysis', {}).get('calls_with_created_contracts', []),
        'potential_attacker': data.get('attack_analysis', {}).get('potential_attackers', []),
        'balance_change':    data.get('attack_analysis', {}).get('balance_changes', {}),
    }
    
    signals = SignalExtractor({}, tx_analysis, txn, r['chain']).run()
    pred = normalize_signals(signals.raw)
    expected = get_expected_signals(r)
    
    print("Expected:", list(expected))
    print("Predicted:", pred.get("reentrancy_detected", False))
    print("Raw Score:", signals.raw.get("reentrancy_score"))
    if not pred.get("reentrancy_detected"):
        print(">> FALSE NEGATIVE DETECTED <<")
        print("Raw Signals Dump:")
        print(json.dumps(signals.raw, indent=2))

if not found_any:
    print("No Reentrancy files found in cache.")
