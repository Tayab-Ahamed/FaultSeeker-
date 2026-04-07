"""
debug_reentry_signals.py
------------------------
Runs _check_reentrancy() against every cached forensics JSON in
data/cache/forensics/ and prints a signal breakdown table.

No RPC calls. No LLM calls. Pure offline analysis.
"""
import json
import os
import sys

_HERE = os.getcwd()
sys.path.insert(0, _HERE)

from faultseeker.forensics.signal_extractor import SignalExtractor

FORENSICS_DIR = os.path.join(_HERE, 'data', 'cache', 'forensics')


def run_signals(txhash: str, cached: dict) -> dict:
    """
    Extract reentrancy debug components from a forensics cache dict.
    The forensics JSON may contain 'tx_analysis' + 'txn_seq' sub-dicts,
    or may be the tx_analysis directly.
    """
    tx_analysis = cached.get('tx_analysis') or cached
    txn_seq     = cached.get('txn_seq') or cached

    if 'trace' not in tx_analysis and 'trace' in cached:
        tx_analysis = dict(tx_analysis)
        tx_analysis['trace'] = cached['trace']

    extractor = SignalExtractor(txn_seq, tx_analysis, txhash, 'eth')
    extractor._check_reentrancy()
    return getattr(extractor, '_reentrancy_debug_components', {})


def main():
    if not os.path.isdir(FORENSICS_DIR):
        print(f"Directory not found: {FORENSICS_DIR}")
        print("Run a transaction first to populate the cache.")
        return

    json_files = sorted(f for f in os.listdir(FORENSICS_DIR) if f.endswith('.json'))
    if not json_files:
        print(f"No JSON files in {FORENSICS_DIR}")
        return

    print(f"Found {len(json_files)} cached file(s). Analysing...\n")

    rows = []
    for fname in json_files:
        txhash = fname[:-5]
        try:
            with open(os.path.join(FORENSICS_DIR, fname), encoding='utf-8', errors='replace') as fh:
                cached = json.load(fh)
        except Exception as e:
            print(f"  [skip] {txhash[:16]}... -- {e}")
            continue
        rows.append((txhash, run_signals(txhash, cached)))

    hdr = (f"{'TX Hash (first 20)':<22} {'score':>5} {'gate':>5} "
           f"{'same_addr':>10} {'anc_prox':>9} {'same_sel':>9} "
           f"{'dc_proxy':>9} {'rebound':>8} {'depth':>6} {'ext':>5}")
    print(hdr)
    print('-' * len(hdr))

    for txhash, d in rows:
        gate = 'Y' if d.get('structural_gate_passed') else 'N'
        print(
            f"{txhash[:20]:<22} "
            f"{d.get('score', 0):>5.0f} "
            f"{gate:>5} "
            f"{d.get('same_contract_reentry', 0):>10} "
            f"{d.get('ancestor_proximity_reentry', 0):>9} "
            f"{d.get('same_selector_reentry', 0):>9} "
            f"{d.get('delegatecall_proxy_reentry', 0):>9} "
            f"{d.get('depth_rebound_peaks', 0):>8} "
            f"{d.get('call_depth_max', 0):>6} "
            f"{d.get('external_calls', 0):>5}"
        )

    print(f"\nDone. {len(rows)} trace(s) analysed.")


if __name__ == '__main__':
    main()
