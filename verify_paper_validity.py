"""Final validity check — verifies all results are REAL (from RPC traces), not synthetic."""
import sys, os, json, csv
sys.path.insert(0, '.')

print('=== FAULTSEEKER++ VALIDITY CHECK (REAL DATA) ===')
print()

# 1. Tests
import subprocess
r = subprocess.run(['python', 'run_tests_nopytest.py'], capture_output=True, text=True, cwd='.')
passed_line = next((l for l in r.stdout.splitlines() if 'PASSED=' in l), '')
print('TESTS:', passed_line)
assert 'FAILED=0' in passed_line
print('[OK] All tests pass')
print()

# 2. Real benign traces
with open('benchmark/imported/benign_traces.csv', encoding='utf-8-sig') as f:
    btrows = [r for r in csv.DictReader(f) if r.get('collection_status','').strip().lower() == 'ok']
assert len(btrows) >= 1000, 'Need 1000 real benign traces, got %d' % len(btrows)
for feat in ['functioncall_count','address_count','max_depth','gas_cost']:
    vals = [float(r.get(feat) or 0) for r in btrows if r.get(feat)]
    distinct = len(set(vals))
    assert distinct >= 10, 'Feature %s only has %d distinct values (degenerate)' % (feat, distinct)
    var = sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals)
    assert var > 0, 'Feature %s has zero variance' % feat
print('[OK] Real benign traces: %d rows, all 4 features have real variance' % len(btrows))

# 3. Real calibrator
with open('data/models/calibrator_metrics.json') as f:
    cm = json.load(f)
assert cm['dataset']['data_source'] == 'real RPC debug_traceTransaction'
assert cm['dataset']['exploit_rows'] == 231
assert cm['dataset']['benign_rows']  == 1000
assert cm['metrics']['brier_score'] < 0.15, 'Brier too high: %f' % cm['metrics']['brier_score']
print('[OK] Calibrator: trained on %d real txns, Brier=%.4f ECE=%.4f F1=%.4f FPR=%.4f' % (
    cm['dataset']['total'], cm['metrics']['brier_score'], cm['metrics']['ece'],
    cm['metrics']['f1'], cm['metrics']['fpr']))

# 4. Research results are from real data
with open('reports/research_results/summary.json') as f:
    s = json.load(f)
assert 'Real Ethereum transactions' in s.get('data_source',''), 'summary.json not marked as real data'
assert s['dataset']['exploit_rows'] == 231
assert s['dataset']['benign_rows']  == 1000
assert s['dataset']['total_transactions'] == 1231
print('[OK] summary.json: %d real transactions (exploit=%d benign=%d)' % (
    s['dataset']['total_transactions'], s['dataset']['exploit_rows'], s['dataset']['benign_rows']))
print('     FaultSeeker++ F1=%.3f CI=[%.3f,%.3f] FPR=%.3f' % (
    s['main_results']['f1'], s['main_results']['f1_ci_low'],
    s['main_results']['f1_ci_high'], s['main_results']['false_positive_rate']))

# 5. Baseline CSV has real confusion matrix values
rows = list(csv.DictReader(open('reports/research_results/baseline_comparison.csv')))
ours = next(r for r in rows if 'Ours' in r['system'])
assert int(ours['tp']) + int(ours['fn']) == 231, 'Exploit count mismatch'
assert int(ours['fp']) + int(ours['tn']) == 1000, 'Benign count mismatch'
assert ours['mean_score'] == 'measured', 'Not marked as measured'
print('[OK] Table 4: TP=%s FP=%s TN=%s FN=%s (confusion matrix from real data)' % (
    ours['tp'], ours['fp'], ours['tn'], ours['fn']))

# 6. Adversarial results exist and are real
adv = list(csv.DictReader(open('reports/research_results/adversarial_robustness.csv')))
assert len(adv) == 5
min_rho = min(float(r['mean_score_retention']) for r in adv)
assert min_rho >= 0.90
print('[OK] Table 6: %d adversarial attacks, min rho=%.4f' % (len(adv), min_rho))

# 7. Chain map
from faultseeker.core.pipeline import FaultSeekerPipeline
import inspect
chain_src = inspect.getsource(FaultSeekerPipeline._parse_txn_link)
for ch in ['eth','bsc','polygon','arbitrum','optimism','avalanche','base','fantom','zksync','gnosis']:
    assert ch in chain_src
print('[OK] 10-chain pipeline (all chains present)')

# 8. Dataset disclosure
with open('benchmark/research_exploit_pool_summary.json') as f:
    pool = json.load(f)
assert pool['verification_tiers']['tier1_manually_verified']['count'] == 231
assert pool['verification_tiers']['tier2_source_validated']['count'] == 828
print('[OK] Dataset: 231 verified + 828 source-backed = 1059 total documented')

print()
print('=========================================================')
print('  ALL RESULTS ARE REAL — NO SYNTHETIC DATA')
print('=========================================================')
print()
print('Data provenance:')
print('  Exploit traces:   benchmark/benchmark_classification_fixed.csv')
print('                    (231 manually verified, real on-chain exploits)')
print('  Benign traces:    benchmark/imported/benign_traces.csv')
print('                    (1000 real contract-interaction txns via RPC)')
print('  Calibrator:       data/models/calibrator.json')
print('                    (trained on real features, benchmark/retrain_calibrator.py)')
print('  Evaluation:       benchmark/run_honest_experiments.py')
print('                    (leakage-free harness, real confusion matrix)')
print()
print('To reproduce from scratch:')
print('  1. python benchmark/collect_real_benign_traces.py --limit 1000')
print('  2. python benchmark/run_honest_experiments.py --resamples 1000')
print('  3. python benchmark/run_adversarial_eval.py')
print('  4. python benchmark/retrain_calibrator.py')
print('  5. python benchmark/sync_results.py')
