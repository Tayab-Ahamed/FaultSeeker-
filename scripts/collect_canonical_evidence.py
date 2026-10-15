"""Preserve requested canonical Git blobs, without checkout or executing upstream code.

Only an explicit allowlist is exported: no credentials or executable configuration.
Git membership proves repository provenance, not the truth of an experiment.
"""
import csv
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/canonical_history'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode())


def csv_inventory(raw):
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    hash_key = next((k for k in ('txn_hash', 'tx_hash', 'transaction_hash', 'hash', 'Transaction Hash')
                     if rows and k in rows[0]), None)
    chain_key = next((k for k in ('chain', 'blockchain', 'Chain') if rows and k in rows[0]), None)
    return {'rows': len(rows), 'physical_data_lines': max(0, len(raw.splitlines()) - 1),
            'blank_lines': sum(not line.strip() for line in raw.splitlines()),
            'columns': list(rows[0]) if rows else [],
            'unique_hashes': len({r[hash_key].lower() for r in rows}) if hash_key else None,
            'chains': sorted({r[chain_key] for r in rows}) if chain_key else [],
            'reentrancy_labeled': sum('reentran' in r.get('vuln_type', '').lower() for r in rows),
            'malformed_evm_hashes': sum(not re.fullmatch(r'0x[0-9a-fA-F]{64}', r[hash_key]) for r in rows) if hash_key else None,
            'unique_vuln_type_strings': len({r.get('vuln_type', '') for r in rows})}


def original_partition(original, current):
    if not original <= current:
        raise ValueError('Original ground truth missing in current tree')
    return {'original': sorted(original), 'reconstruction': sorted(current - original)}


def metric_scope(name):
    return {'runtime_cost.json': 'MODELED-NOT-MEASURED',
            'reentrancy_metrics.json': 'NO-EVALUATED-PREDICTIONS',
            'honest_research_tables.tex': 'RECORDED-TABLE-REQUIRES-RUN-LINEAGE',
            'localization_metrics.json': 'RECORDED-AGGREGATE-REQUIRES-RAW-PREDICTIONS'
            }.get(name, 'SOURCE-ARTIFACT-NOT-AUTOMATIC-VERIFICATION')


def collect():
    refs = git('for-each-ref', '--format=%(refname) %(objectname)', 'refs/remotes/canonical').decode().splitlines()
    commits = git('rev-list', *[r.split()[0] for r in refs]).decode().splitlines()
    entries = []

    def export(ref, path, category):
        commit = git('rev-parse', ref).decode().strip()
        blob = git('rev-parse', commit + ':' + path).decode().strip()
        raw = git('cat-file', 'blob', blob)
        dest = BASE / 'snapshots' / commit / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        record = {'commit': commit, 'source_path': path, 'git_blob_sha1': blob,
                  'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                  'cache': dest.relative_to(ROOT).as_posix(), 'category': category,
                  'evidence_scope': metric_scope(Path(path).name)}
        if record not in entries:
            entries.append(record)
        return raw, record

    histories = {}
    for commit in commits:
        listing = git('ls-tree', '-r', '--name-only', commit, 'benchmark/benchmark_classification_fixed.csv').decode().splitlines()
        if not listing:
            continue
        path = listing[0]
        blob = git('rev-parse', commit + ':' + path).decode().strip()
        if blob not in histories:
            raw, entry = export(commit, path, 'cohort-version')
            histories[blob] = dict(csv_inventory(raw), sha256=entry['sha256'], cache=entry['cache'], commits=[])
        histories[blob]['commits'].append(commit)

    original = set(git('ls-tree', '-r', '--name-only', 'fca6b99', 'benchmark/ground_truth').decode().splitlines())
    current = set(git('ls-tree', '-r', '--name-only', 'canonical/main', 'benchmark/ground_truth').decode().splitlines())
    partitions = original_partition(original, current)
    origins = []
    for kind, paths in partitions.items():
        for path in paths:
            ref = 'fca6b99' if kind == 'original' else 'canonical/main'
            raw, entry = export(ref, path, 'ground-truth-' + kind)
            first = git('log', '--reverse', '--diff-filter=A', '--format=%H %aI', 'canonical/main', '--', path).decode().splitlines()
            origins.append({'path': path, 'kind': kind, 'first_add': first[0] if first else None,
                            'sha256': entry['sha256'], 'cache': entry['cache']})

    for ref in ('canonical/main', '50853e4', '3b910a1', '8e02f92', 'fca6b99', 'ecdb430', 'cf9e5b2'):
        paths = git('ls-tree', '-r', '--name-only', ref, 'reports/honest_results', 'reports/research_results',
                    'reports/SYNTHETIC_DO_NOT_CITE', 'benchmark/honest_eval',
                    'benchmark/run_honest_experiments.py', 'benchmark/compute_cost.py',
                    'benchmark/compute_metrics.py', 'benchmark/run_localization_eval.py',
                    'benchmark/calibrator_cv_metrics.json', 'data/models/calibrator_cv_metrics.json',
                    'benchmark/dataset_sources.json', 'benchmark/DATASET_INTEGRITY.md',
                    'benchmark/imported/benign_traces.csv').decode().splitlines()
        for path in paths:
            export(ref, path, 'versioned-results-or-method')
    for path in ('EVALUATION_PROTOCOL.md', 'PAPER_CLAIM_AUDIT.md'):
        export('f055c75^', path, 'recovered-deleted-document')

    write(BASE / 'manifest.json', {'remote_url': 'https://github.com/Tayab-Ahamed/FaultSeeker-.git',
          'refs': refs, 'reachable_commits': commits, 'shallow': git('rev-parse', '--is-shallow-repository').decode().strip(),
          'scope': 'All advertised branches/history; no unadvertised, deleted or private refs asserted', 'artifacts': entries})
    write(BASE / 'cohort_history.json', {'versions': histories,
          'has_246_row_version': any(v['rows'] == 246 for v in histories.values()),
          'ground_truth_counts': {k: len(v) for k, v in partitions.items()}, 'ground_truth_origins': origins})
    print(json.dumps({'cached_artifacts': len(entries), 'cohort_versions': len(histories),
                      'row_counts': sorted({v['rows'] for v in histories.values()}),
                      'ground_truth': {k: len(v) for k, v in partitions.items()}}))


if __name__ == '__main__':
    collect()
