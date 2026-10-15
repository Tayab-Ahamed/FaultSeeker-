"""Publish all claim decisions, their exact commits and post-commit test evidence."""
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_canonical_evidence import BASE, write
from scripts.commit_canonical_decisions import check, record_gate, stage_commit


def call_count_bin(row):
    """Missing or invalid observations stay unavailable, never zero-filled."""
    try:
        count = float(row.get('functioncall_count', ''))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(count) or count < 0:
        return None
    return ('Simple' if count <= 5 else 'Moderate' if count <= 50 else
            'Complex' if count <= 500 else 'Exceptionally Complex')


def finalize():
    check()
    decisions = json.loads((BASE / 'verification.json').read_text())
    expected = {3, 4, 5, 6, 7, 8, 13, 14, 15, 17, 18, 21, 22, 25, 27, 28, 29, 30}
    assert {d['id'] for d in decisions['decisions']} == expected
    assert len(decisions['decisions']) == 18
    assert all(d['after']['outcomes'] == {'passed': 367, 'skipped': 1} for d in decisions['decisions'])
    ledger = ROOT / 'data/research/spend_ledger.json'
    accounting = json.loads((BASE / 'accounting.json').read_text())
    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == accounting['ledger_sha256']
    assert accounting['cumulative_booked_usd'] <= 10
    paper = Path(r'C:\Users\91701\Downloads\Implementation_Paper (1).pdf')
    assert hashlib.sha256(paper.read_bytes()).hexdigest() == json.loads((BASE / 'paper_vs_repo.json').read_text())['paper_sha256']

    environment = os.environ.copy()
    for name, key in [('solc', 'SOLC_BINARY'), ('anvil', 'ANVIL_BINARY'), ('cast', 'CAST_BINARY')]:
        environment[key] = str(ROOT / 'build/tools' / (name + '.exe'))
    environment['FAULTSEEKER_RUN_HISTORICAL_REPLAY'] = '0'
    wrapper = '''import sys,socket,runpy
sys.modules['readline']=None
original=socket.socket.connect
def offline(self,address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','localhost','::1'):
        raise OSError('Final verification prohibits external network')
    return original(self,address)
socket.socket.connect=offline
script=sys.argv.pop(1)
sys.argv[0]=script
runpy.run_path(script,run_name='__main__')
'''
    command = [sys.executable, '-c', wrapper, str(ROOT / 'scripts/reproduce_paper.py'),
               '--require-claim-closure', '--dataset', str(ROOT / 'reports/provenance_hunt/cohort/records.json'),
               '--evidence-root', str(ROOT / 'reports/provenance_hunt/cohort')]
    log = ROOT / 'build/closure_acceptance/canonical-strict.log'
    with log.open('wb') as handle:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Strict closure failed; inspect build/closure_acceptance/canonical-strict.log')
    report = json.loads((ROOT / 'reports/local_verification/claim_report.json').read_text())
    assert report['closure']['statuses'] == {'VERIFIED': 13, 'UNVERIFIABLE': 18}
    assert report['original_test_evidence']['original_sources_changed'] == []
    manifest = json.loads((BASE / 'manifest.json').read_text())
    # Reproducing an old table does not validate its controls. The July strict
    # harness lacked the later distinct-vector degeneracy check.
    strict_commit = json.loads((BASE / 'findings.json').read_text())['reruns']['50853e4']['commit']
    benign_input = next(item for item in manifest['artifacts'] if item['commit'] == strict_commit
                        and item['source_path'] == 'benchmark/imported/benign_traces.csv')
    with (ROOT / benign_input['cache']).open(encoding='utf-8-sig', newline='') as handle:
        benign_rows = list(csv.DictReader(handle))
    feature_names = ['functioncall_count', 'address_count', 'max_depth', 'gas_cost']
    vectors = Counter(tuple(row.get(k) for k in feature_names) for row in benign_rows)
    write(BASE / 'strict_control_audit.json', {'commit': strict_commit, 'input': benign_input,
        'benign_rows': len(benign_rows), 'distinct_feature_vectors': len(vectors),
        'feature_names': feature_names, 'vector_counts': [{'vector': list(k), 'count': v} for k, v in vectors.items()],
        'verdict': 'The reproduced .8593 result uses a degenerate benign control population: 1000 rows, one feature vector. Numerical reproducibility is not credible end-to-end discrimination evidence.'})
    assert len(benign_rows) == 1000 and len(vectors) == 1
    cohort = json.loads((BASE / 'cohort_history.json').read_text())
    variants = []
    for version in cohort['versions'].values():
        with (ROOT / version['cache']).open(encoding='utf-8-sig', newline='') as handle:
            records = list(csv.DictReader(handle))
        bins = Counter(call_count_bin(row) for row in records if call_count_bin(row) is not None)
        variants.append({'rows': len(records), 'input_sha256': version['sha256'],
            'chain_counts': dict(Counter(row['chain'] for row in records)),
            'ethereum_share_percent': 100 * sum(row['chain'] == 'eth' for row in records) / len(records),
            'stored_class_counts': dict(Counter(row['class'] for row in records)),
            'call_count_bins': dict(bins),
            'unavailable_call_count_rows': sum(call_count_bin(row) is None for row in records),
            'call_count_bin_percent': {k: 100*v/len(records) for k, v in bins.items()},
            'percent_denominator': 'All rows, including unavailable rows; no implicit zero or denominator shrinkage',
            'stored_class_disagrees_with_available_call_count_bin': sum(row['class'] != call_count_bin(row)
                for row in records if call_count_bin(row) is not None)})
    write(BASE / 'cohort_definition_audit.json', {'versions': variants,
        'scope': 'CSV descriptive arithmetic only. functioncall_count is not proven to mean unique executed functions; binning this column does not authenticate the paper complexity definition.'})
    map_path = BASE / 'PAPER_VS_REPO.md'
    map_text = map_path.read_text(encoding='utf-8')
    if '## Additional strict-control audit' not in map_text:
        map_path.write_bytes((map_text + '\n## Additional strict-control audit\n\n'
            'The older .8593 run uses **1000 benign rows with exactly one distinct four-feature vector**. '
            'Its coverage gate checked populated columns but did not detect this degeneracy. '
            'The .8593 table is reproducible arithmetic on an unsuitable control population, not a stronger alternative '
            'to the later CV result. Exact input identity and counted vector are in `strict_control_audit.json`. '
            'This additional finding does not promote any claim or change the immutable decision-map JSON.\n').encode())
    map_text = map_path.read_text(encoding='utf-8')
    if '## Complexity definition check' not in map_text:
        map_path.write_bytes((map_text + '\n## Complexity definition check\n\n'
            'Applying the stated 5/50/500 boundaries to the stored `functioncall_count` column gives '
            '14/136/49/32 records in the four bins at 231 rows, and 14/148/50/34 at 246 rows. '
            'These differ both from the stored class labels and the paper proportions. '
            'Call count is not proven to mean unique functions, so these are conditional descriptive bins, '
            'not replacement authenticated complexity outcomes. Ethereum is 142/246 (57.7236%) in the early CSV, '
            'as well as 132/231 (57.1429%) in the requested frozen version. '
            'Exact input hashes and all version counts: `cohort_definition_audit.json`.\n').encode())
    index = ['# Canonical evidence index', '',
             'All snapshots preserve Git blob bytes. The manifest additionally includes every individual original/reconstructed GT file and versioned method/result dependency.', '',
             '| Category | Full commit | Source / cached evidence | SHA-256 |', '|---|---|---|---|']
    selected = {'cohort-version', 'recovered-deleted-document', 'requested-231-row-snapshot', 'label-reading-legacy-scorer'}
    main_commit = next(r.split()[1] for r in manifest['refs'] if r.split()[0] == 'refs/remotes/canonical/main')
    for item in manifest['artifacts']:
        if item['category'] in selected or (item['commit'] == main_commit and item['category'] == 'versioned-results-or-method'):
            relative = (ROOT / item['cache']).relative_to(BASE).as_posix()
            index.append(f"| {item['category']} | `{item['commit']}` | [{item['source_path']}]({relative}) | `{item['sha256']}` |")
    index += ['', '## Reproduction', '',
        '1. `python scripts/collect_canonical_evidence.py` exports only allowlisted public artifacts from the fetched refs.',
        '2. `python scripts/reproduce_canonical_harness.py` reruns reviewed historical numerical scorers with all networking denied.',
        '3. `python scripts/analyze_canonical_evidence.py` derives counts and bounded history searches.',
        '4. `python scripts/report_canonical_decisions.py` renders the publication-scope map.',
        '', 'These regeneration commands overwrite evidence files. Run them in a separate review checkout: the current registry binds existing hashes, and regenerated experiment timestamps may change file digests.',
        '', 'Commit helpers are explicit maintainer operations, not reproduction prerequisites. No upstream executable application or secret-bearing configuration is checked out or executed.']
    (BASE / 'EVIDENCE_INDEX.md').write_bytes(('\n'.join(index) + '\n').encode())
    rows = [json.loads(p.read_text()) for p in sorted((ROOT / 'reports/claim_closure/claims').glob('*.json'))]
    by_id = {d['id']: d for d in decisions['decisions']}
    lines = ['# Canonical evidence review: complete 31-claim registry', '',
             '13 VERIFIED within existing implementation/sample scopes; 18 UNVERIFIABLE publication outcomes after canonical review. No claim promoted from inference, literal reports, proxy models or fixtures.', '',
             'Detailed numbers and scope: [paper versus repository map](PAPER_VS_REPO.md). Exact cached bytes and Git identities: [manifest](manifest.json).', '',
             '| Claim | Title | Status | Canonical verdict | Decision commit |', '|---|---|---|---|---|']
    for row in rows:
        d = by_id.get(row['id'])
        if d:
            commit = d['commit']
        else:
            commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--',
                       f"reports/claim_closure/claims/{row['id']:02d}.json"], cwd=ROOT, text=True).strip()
        lines.append(f"| {row['id']} | {row['claim']} | {row['status']} | {row.get('paper_verdict', 'Prior verification scope unchanged')} | `{commit}` |")
    lines += ['', '## Validation', '',
        '- Every reopened decision has its own commit, a full-suite pre-commit gate and a full-suite post-commit gate. Exact commits and SHA-256-bound compressed JUnit files are in `verification.json`.',
        '- 367 passed, 1 skipped at each completed gate. The single skip is the explicitly opt-in live historical replay; the recorded historical replay and local compiled execution checks pass.',
        '- All 201 original tests pass, their source digests unchanged. Strict closure verifies every evidence digest and all 31 terminal decisions; it does not mean all paper claims are true.',
        '- Uploaded paper hash unchanged. No model weights, thresholds, current benchmark rows or paper text modified in this review.',
        f"- New paid API/RPC requests:0; new paid spend:$0. Cumulative conservative booked spend:${accounting['cumulative_booked_usd']:.6f}/$10; ledger unchanged.",
        '- Canonical remote fetched; no merge, checkout of upstream, push or PR. Kluster local waiver continues; full AGENTS.md review must resume before any push/PR.', '',
        '## Principal corrections', '',
        '- A 246-row historical CSV DOES exist: 246 unique parsed records, 248 physical data lines including two blanks, 15 malformed hashes, 8 chains. The claimed authenticity and 10-chain study remain unsupported.',
        '- Original 115 GT files (April 3) and 48 October reconstructions are separately cached. Original files cover 114 unique transaction hashes; duplicate SorStaking affects independence of localization targets.',
        '- .8593 [.8223,.8950] and .7586 [.7071,.8040] reproduce as distinct historical feature-harness runs. They are not TableV SSTORE or live LLM results. The newer stored -TIG row does not reproduce: observed .6531 versus recorded .6565.',
        '- The older .8593 run has a degenerate benign control population: 1000 rows, one distinct feature vector. See strict_control_audit.json; reproduction is not validation of study design.',
        '- Localization6.09% is a recovered aggregate (7/115 targets), with no raw rankings tracked in any of53 reachable canonical commits. It cannot verify68->81% guidance.',
        '- Overall35% is modeled arithmetic;58.3% applies only to Tier2. Real measured savings, TableV metrics, TableVI component means and guidance effect remain unavailable.']
    (BASE / 'CLAIM_STATUS.md').write_bytes(('\n'.join(lines) + '\n').encode())
    decisions['final_strict_closure'] = report['closure']
    decisions['final_original_test_evidence'] = report['original_test_evidence']
    decisions['paper_sha256_unchanged'] = hashlib.sha256(paper.read_bytes()).hexdigest()
    decisions['ledger_unchanged'] = True
    decisions['new_paid_requests'] = 0
    write(BASE / 'verification.json', decisions)
    progress_path = ROOT / 'reports/claim_closure/progress.json'
    progress = json.loads(progress_path.read_text())
    progress.update(canonical_review_complete=True, canonical_reviewed_ids=sorted(expected),
                    canonical_statuses=report['closure']['statuses'],
                    canonical_paper_map=(BASE / 'PAPER_VS_REPO.md').relative_to(ROOT).as_posix(),
                    canonical_decision_commits={str(d['id']): d['commit'] for d in decisions['decisions']})
    write(progress_path, progress)
    _, pre = record_gate('canonical-final-pre')
    paths = [p for p in BASE.rglob('*') if p.is_file()]
    paths += [ROOT / 'scripts/finalize_canonical_review.py']
    paths.append(ROOT / 'tests/test_canonical_evidence.py')
    paths.append(ROOT / '.gitattributes')
    paths.append(progress_path)
    paths += [p for p in (ROOT / 'reports/local_verification').rglob('*') if p.is_file()]
    commit = stage_commit(paths, 'claim30: publish canonical paper-number map and all decision/test evidence')
    _, post = record_gate('canonical-final-post')
    # The final post-commit JUnit remains in ignored build, so reporting it leaves
    # no unstaged artifact. Its pass/fail is observed here, never predeclared.
    target = ROOT / post['junit']
    ignored = ROOT / 'build/closure_acceptance/canonical-final-post.xml.gz'
    ignored.write_bytes(target.read_bytes())
    target.unlink()
    print(json.dumps({'final_commit': commit, 'suite': post['outcomes'], 'closure': report['closure']['statuses'],
                      'new_paid_cost_usd': 0, 'cumulative_booked_usd': accounting['cumulative_booked_usd']}), flush=True)


if __name__ == '__main__':
    finalize()
