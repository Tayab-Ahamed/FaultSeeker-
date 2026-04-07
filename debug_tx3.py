"""Quick diagnostic for Tx3 signal extraction failure."""
import os, sys, re

TX3 = '0x57b589f631f8ff20e2a89a649c4ec2e35be72eaecf155fdfde981c0fec2be5ba'

# ── 1. Path resolution (same logic as signal_extractor.py) ─────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'data', 'cache', 'replay', f'{TX3}.txt')
print(f"Cache path : {CACHE}")
print(f"File exists: {os.path.exists(CACHE)}")

if not os.path.exists(CACHE):
    print("FAIL: cache file not found — signal extractor cannot read it")
    sys.exit(1)

# ── 2. Read & parse exactly as _analyze_cast_trace_text does ───────────────
raw = open(CACHE, encoding='utf-8', errors='ignore').read()
print(f"File bytes : {len(raw)}")
print(f"Raw (repr) :\n{repr(raw[:500])}")

lines = raw.splitlines()
print(f"\nLine count : {len(lines)}")
for i, line in enumerate(lines):
    print(f"  line[{i}] = {repr(line)}")

# ── 3. Delegatecall detection ───────────────────────────────────────────────
has_delegatecall = False
for line in lines:
    low = line.lower()
    if '[delegatecall]' in low or 'delegatecall' in low:
        has_delegatecall = True
        print(f"\n✅ delegatecall found in line: {repr(line)}")

if not has_delegatecall:
    print("\n❌ delegatecall NOT found in any line")

# ── 4. Now run actual signal extractor ─────────────────────────────────────
sys.path.insert(0, HERE)
from faultseeker.forensics.signal_extractor import SignalExtractor, _REPLAY_CACHE_DIR

print(f"\n_REPLAY_CACHE_DIR = {_REPLAY_CACHE_DIR}")
print(f"Matches HERE?     {os.path.normpath(_REPLAY_CACHE_DIR) == os.path.normpath(os.path.join(HERE, 'data', 'cache', 'replay'))}")

se = SignalExtractor({}, {}, TX3, 'bsc')
print(f"\nCache path in extractor: {se._cast_cache_path}")
print(f"Exists from extractor  : {os.path.exists(se._cast_cache_path)}")

# Run only the cast text method
se._analyze_cast_trace_text()
s = se.signals
print(f"\nAfter _analyze_cast_trace_text():")
print(f"  access_control_bypass    = {s.access_control_bypass}")
print(f"  closed_source_state_change = {s.closed_source_state_change}")
print(f"  hashed_fn_count          = {s.hashed_fn_count}")
print(f"  single_transfer_only     = {s.single_transfer_only}")
print(f"  inflation_attack         = {s.inflation_attack}")
