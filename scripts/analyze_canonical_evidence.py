"""Derive bounded historical evidence findings; never promote a recorded metric."""
import ast
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_canonical_evidence import BASE, csv_inventory, git, write


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    cohort = json.loads((BASE / 'cohort_history.json').read_text())

    def export(ref, path, category):
        commit = git('rev-parse', ref).decode().strip()
        raw = git('show', commit + ':' + path)
        dest = BASE / 'snapshots' / commit / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        entry = {'commit': commit, 'source_path': path, 'category': category,
                 'git_blob_sha1': git('rev-parse', commit + ':' + path).decode().strip(),
                 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                 'cache': dest.relative_to(ROOT).as_posix(),
                 'evidence_scope': 'Repository provenance only; evaluate method before citing'}
        if not any(e['commit'] == commit and e['source_path'] == path for e in manifest['artifacts']):
            manifest['artifacts'].append(entry)
        return raw, entry

    raw, frozen = export('fca6b99', 'benchmark/benchmark_classification_fixed.csv', 'requested-231-row-snapshot')
    for ref in ('3b910a1', '50853e4'):
        export(ref, 'benchmark/run_research_experiments.py', 'label-reading-legacy-scorer')
    for ref in ('50853e4', '8e02f92'):
        export(ref, 'faultseeker/research/calibration.py', 'reviewed-historical-numerical-dependency')
    for name in ('benchmark/fetch_selector_names.py', 'benchmark/evaluate_localization_with_resolution.py'):
        if git('ls-tree', '--name-only', 'canonical/main', name).strip():
            export('canonical/main', name, 'localization-method')
    for version in cohort['versions'].values():
        version.update(csv_inventory((ROOT / version['cache']).read_bytes()))
    cohort['has_246_row_version'] = any(v['rows'] == 246 for v in cohort['versions'].values())
    originals = [json.loads((ROOT / x['cache']).read_text(encoding='utf-8-sig'))
                 for x in cohort['ground_truth_origins'] if x['kind'] == 'original']
    hashes = Counter(h.lower() for row in originals for h in row.get('transaction_hash', []))
    cohort['original_ground_truth_audit'] = {
        'files': len(originals), 'unique_transaction_hashes': len(hashes),
        'duplicate_hashes': {k: v for k, v in hashes.items() if v > 1},
        'fields': dict(Counter(k for row in originals for k in row)),
        'explicit_annotator_attestations': sum('annotators' in row for row in originals),
        'scope': 'Original repository annotations with locations/disclosure links; not two independent qualified annotation attestations'}
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    cohort['requested_231_snapshot'] = dict(csv_inventory(raw), commit=frozen['commit'], sha256=frozen['sha256'],
        chain_counts=dict(Counter(r['chain'] for r in rows)), class_counts=dict(Counter(r['class'] for r in rows)),
        original_gt_overlap=len(set(hashes) & {r['txn_hash'].lower() for r in rows}))

    # Search all reachable canonical versions of selected text source/artifact paths.
    # git grep returns only matching lines. Secrets/configuration are excluded by path.
    query = r'(^|[^0-9])(68[[:space:]]*%.*81[[:space:]]*%|0\.68[^0-9].*0\.81)'
    import subprocess
    refs = [r.split()[0] for r in manifest['refs']]
    commits = manifest['reachable_commits']
    search = subprocess.run(['git', 'grep', '-I', '-n', '-E', query, *commits, '--',
                             '*.md', '*.py', '*.tex', 'reports/*.json'], cwd=ROOT, capture_output=True)
    if search.returncode not in (0, 1):
        raise RuntimeError('Canonical guidance history search failed')
    (BASE / 'guidance_history_search.txt').write_bytes(search.stdout)
    write(BASE / 'history_search.json', {'refs': refs, 'commits': len(commits), 'guidance_regex': query,
        'guidance_matching_lines': len(search.stdout.splitlines()),
        'scope': 'Canonical reachable text versions, selected source/report/doc paths; no private or deleted unreachable history asserted',
        'tracked_data_output_files_by_commit': {c: len(git('ls-tree', '-r', '--name-only', c, 'data/output').splitlines()) for c in commits},
        'compound_case': 'Compound-named exploit annotations exist, but none supplies an identified legitimate cToken recursion control tied to the paper narrative. A hash cannot be chosen by inference.'})

    reruns = {}
    for ref in ('50853e4', '8e02f92'):
        commit = git('rev-parse', ref).decode().strip()
        folder = BASE / 'reruns' / commit
        status = json.loads((folder / 'status.json').read_text())
        reruns[ref] = {'commit': commit, 'status': status['status'], 'systems': status['systems'],
                       'scope': 'Offline feature/proxy classifier, not end-to-end SSTORE detector or live LLM quality'}
    current = git('rev-parse', 'canonical/main').decode().strip()
    folder = BASE / 'snapshots' / current
    localization = json.loads((folder / 'reports/honest_results/localization_metrics.json').read_text())
    cost = json.loads((folder / 'reports/research_results/runtime_cost.json').read_text())
    reentrancy = json.loads((folder / 'reports/research_results/reentrancy_metrics.json').read_text())
    write(BASE / 'findings.json', {'cohort': cohort['requested_231_snapshot'], 'reruns': reruns,
        'localization': {'recorded_metrics': localization['metrics'], 'corpus': localization['corpus'],
                         'unique_provenance_transactions': len(localization['predictions_provenance']),
                         'duplicate_gt_explains_115_targets_114_tx': len(hashes) == 114 and len(originals) == 115,
                         'raw_predictions_recovered': False,
                         'verdict': 'Recorded 7/115 = 6.09%; duplicate GT transaction means 115 targets are not 115 independent transactions; raw rankings unavailable'},
        'cost': cost, 'reentrancy': reentrancy,
        'correction_to_task_premise': 'A 246-record/246-unique-hash historical CSV exists. 248 physical data lines include two blanks. It contains malformed hashes and only 8 chains, so it does not verify 246 authentic adjudicated exploits.'})
    write(BASE / 'cohort_history.json', cohort)
    write(BASE / 'manifest.json', manifest)
    print(json.dumps({'cohort_versions': [{k: v[k] for k in ('rows', 'physical_data_lines', 'unique_hashes', 'reentrancy_labeled', 'malformed_evm_hashes')} for v in cohort['versions'].values()],
                      'guidance_matches': len(search.stdout.splitlines()), 'original_unique_hashes': len(hashes)}))


if __name__ == '__main__':
    main()
