import sys, os, json
sys.path.insert(0, os.getcwd())
from faultseeker.forensics.orchestrator import ForensicsOrchestrator

orch = ForensicsOrchestrator()
hashes = [
    '0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6',
    '0x6bfd9e286e37061ed279e4f139fbc03c8bd707a2cdd15f7260549052cbba79b7'
]

with open('target_output.txt', 'w') as out:
    for h in hashes:
        out.write(f"\n====================================\n Evaluating: {h}\n")
        try:
            res, _, _ = orch.run(h, 'eth')
            if res:
                raw = res.signals.raw
                out.write(f"Raw Score: {raw.get('reentrancy_score', 0)}\n")
                out.write(f"Reentrancy Detected: {(raw.get('reentrancy_score', 0) > 0)}\n")
                out.write(f"All raw signals: {json.dumps(raw, indent=2)}\n")
            else:
                out.write("Failed: Pipeline returned None (Trace timeout)\n")
        except Exception as e:
            out.write(f"Exception: {e}\n")
