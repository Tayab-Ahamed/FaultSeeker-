"""
Dataset Validation Script — FaultSeeker++ Benchmark
Checks: row count, duplicate TXs, chain distribution, vuln type breakdown
"""
import csv
from collections import Counter

CSV_PATH = "benchmark_classification_fixed.csv"

hashes = []
chains = []
vuln_types = []
difficulty = []

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        txn = row["txn_hash"].strip()
        if txn:
            hashes.append(txn)
            chains.append(row["chain"].strip().lower())
            vuln_types.append(row["vuln_type"].strip())
            difficulty.append(row["class"].strip())

total = len(hashes)
dupes = [h for h, c in Counter(hashes).items() if c > 1]

print(f"\n{'='*50}")
print(f"  FaultSeeker++ Dataset Validation Report")
print(f"{'='*50}")
print(f"\n  Total entries   : {total}")
print(f"  Duplicate hashes: {len(dupes)}")
if dupes:
    print(f"   -> Dupes: {dupes}")

print(f"\n  Chain breakdown:")
for chain, count in sorted(Counter(chains).items(), key=lambda x: -x[1]):
    pct = count / total * 100
    bar = '█' * int(pct / 2)
    print(f"    {chain:<12} {count:>4}  ({pct:4.1f}%)  {bar}")

print(f"\n  Difficulty breakdown:")
for diff, count in sorted(Counter(difficulty).items(), key=lambda x: -x[1]):
    print(f"    {diff:<30} {count:>4}")

print(f"\n  Top 10 vulnerability types:")
for vuln, count in Counter(vuln_types).most_common(10):
    print(f"    {vuln:<45}  {count}")

print(f"\n{'='*50}")
print(f"  Target: 160+ entries  |  Status: {'✓ PASSED' if total >= 160 else '✗ FAILED'}")
print(f"{'='*50}\n")
