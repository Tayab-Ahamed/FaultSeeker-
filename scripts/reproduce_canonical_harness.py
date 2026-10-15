"""Replay reviewed historical feature scorers offline, without importing the live app.

These are proxy/feature-classifier results, NOT empirical paper Table V or LLM
conformance. Package initializers are intentionally empty in the scratch tree;
the reviewed numerical modules, inputs and hyperparameters are byte-identical.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_canonical_evidence import git, write


def run(ref):
    commit = git('rev-parse', ref).decode().strip()
    scratch = ROOT / 'build/canonical_harness' / commit
    out = ROOT / 'reports/canonical_history/reruns' / commit
    inputs = []
    paths = ['benchmark/run_honest_experiments.py',
             'benchmark/benchmark_classification_fixed.csv',
             'benchmark/imported/benign_traces.csv',
             'benchmark/honest_eval/features.py', 'benchmark/honest_eval/leakage_guard.py',
             'benchmark/honest_eval/metrics.py', 'faultseeker/research/calibration.py']
    # The historical HF address catalog influences benign joins if it exists.
    optional = 'benchmark/imported/hf_ethereum_benign_transactions.csv'
    if git('ls-tree', '--name-only', commit, optional).strip():
        paths.append(optional)
    for path in paths:
        raw = git('show', commit + ':' + path)
        dest = scratch / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        inputs.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest(),
                       'git_blob_sha1': git('rev-parse', commit + ':' + path).decode().strip()})
    for package in ('benchmark', 'benchmark/honest_eval', 'faultseeker', 'faultseeker/research'):
        dest = scratch / package / '__init__.py'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'')
    out.mkdir(parents=True, exist_ok=True)
    wrapper = '''import sys,socket,runpy
sys.modules['readline']=None
def deny(*a,**k): raise RuntimeError('Historical arithmetic rerun forbids all network')
socket.socket.connect=deny
socket.create_connection=deny
script=sys.argv.pop(1)
sys.argv[0]=script
runpy.run_path(script,run_name='__main__')
'''
    command = [sys.executable, '-c', wrapper, str(scratch / paths[0]), '--results-dir', str(out)]
    with (out / 'stdout.txt').open('wb') as log:
        result = subprocess.run(command, cwd=scratch, stdout=log, stderr=subprocess.STDOUT)
    observed = json.loads((out / 'status.json').read_text()) if (out / 'status.json').exists() else None
    write(out / 'reproduction.json', {'commit': commit, 'exit_code': result.returncode,
        'inputs': inputs, 'scope': 'Offline historical proxy/feature scorer arithmetic, not paper mechanism evaluation',
        'hyperparameters': 'Original defaults, no override, no tuning, no allow-incomparable',
        'network_requests': 0, 'paid_cost_usd': 0, 'status': observed.get('status') if observed else 'NO-OUTPUT'})
    print(ref, result.returncode, [(r['system'], r['f1']) for r in (observed or {}).get('systems', [])], flush=True)
    if result.returncode not in (0, 2):
        raise RuntimeError('Historical harness failed; inspect cached stdout')


if __name__ == '__main__':
    for revision in ('50853e4', '8e02f92'):
        run(revision)
