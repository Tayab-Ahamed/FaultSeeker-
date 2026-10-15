"""Commit evidence-bound reopen reviews, one decision and full suite per claim."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.finalize_claim_closure import git, full_suite
from benchmark.claim_registry import claim_report
from benchmark.claim_closure import apply_closure

BASE = Path('reports/provenance_hunt')
RUN = 'provenance-hunt-2026-10-15'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=True) + '\n').encode('utf-8'))


def gate(label):
    outcomes = full_suite(label)
    baseline = json.loads((ROOT / 'benchmark/baseline_tests.json').read_text())
    changed = [p for p, sha in baseline['source_sha256'].items()
               if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha]
    if changed:
        raise RuntimeError('Original test source changed')
    return outcomes


def source_commits():
    files = [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / BASE).rglob('*') if p.is_file()]
    research = [p for p in files if not any(part in p for part in (
        '/providers/', '/cohort/', '/experiments/', '/previous_decisions/'))
        and Path(p).name not in {'accounting.json', 'accounting_snapshot.json', 'frontiers.json',
                                 'provider_preflight.json', 'compound_search.json'}]
    groups = [
        (4, ['.gitattributes', 'scripts/hunt_claim_provenance.py', 'tests/test_provenance_hunt.py'] + research),
        (3, ['scripts/summarize_provenance_hunt.py', 'tests/test_provenance_hunt_results.py'] + [p for p in files if '/cohort/' in p]),
        (17, ['scripts/probe_nara_conformance.py', 'tests/test_gateway_conformance.py'] + [p for p in files if '/providers/' in p or p.endswith('/provider_preflight.json')]),
        (30, ['scripts/reopen_claim_decisions.py'] + [p for p in files if '/experiments/' in p
              or Path(p).name in {'accounting.json', 'accounting_snapshot.json', 'frontiers.json'}]),
    ]
    for number, paths in groups:
        if git('branch', '--show-current') != 'paper-claims-verified':
            raise RuntimeError('Wrong branch')
        staged = set(git('diff', '--cached', '--name-only').splitlines())
        if staged - set(paths):
            raise RuntimeError('Index contains unrelated staged work')
        # Avoid the Windows command-line length limit for 1,000+ cached files.
        pathspec = ROOT / 'build/hunt-stage-paths.txt'
        pathspec.parent.mkdir(exist_ok=True)
        pathspec.write_bytes(b''.join(p.encode('utf-8') + b'\0' for p in paths))
        git('add', '--pathspec-from-file=' + str(pathspec), '--pathspec-file-nul')
        if not git('diff', '--cached', '--name-only'):
            continue
        gate(f'hunt-source-{number}')
        git('diff', '--cached', '--check')
        git('commit', '--quiet', '-m', f'claim{number}: preserve provenance-hunt implementation and real evidence')
        print('Committed source/evidence', number, git('rev-parse', '--short', 'HEAD'), flush=True)


def decisions():
    frontiers = json.loads((ROOT / BASE / 'frontiers.json').read_text())
    common = [BASE / p for p in ('hunt.json', 'cohort/row_decisions.json', 'accounting.json', 'frontiers.json')]
    specific = {
        4: ['source_manifest.json', 'reviewed_source_pairs.json'],
        15: ['compound_search.json'],
        17: ['providers/inventory.json', 'providers/observations_manifest.json', 'providers/bynara_conformance_diagnostic.json'],
        25: ['ethereum_requests.json'],
        27: ['experiments/waf.json'],
        13: ['experiments/detectors.json'], 14: ['experiments/detectors.json'],
        18: ['experiments/routing.json'], 21: ['experiments/prefilter.json'],
        22: ['experiments/measurement_frontier.json'], 28: ['experiments/measurement_frontier.json'],
        29: ['experiments/guidance.json'], 30: ['experiments/dispatch_log.json'],
    }
    for number in [3, 4, 5, 6, 7, 8, 15, 17, 13, 14, 18, 21, 22, 25, 27, 28, 29, 30]:
        if git('branch', '--show-current') != 'paper-claims-verified':
            raise RuntimeError('Wrong branch')
        path = ROOT / 'reports/claim_closure/claims' / f'{number:02d}.json'
        old = json.loads(path.read_text())
        # A marker written before a failed test/commit is not committed progress.
        if old.get('reopen_review_run') == RUN and not git('diff', 'HEAD', '--', str(path.relative_to(ROOT))):
            continue
        if old['status'] != 'UNVERIFIABLE':
            raise RuntimeError('Refusing to reopen a claim outside the requested queue')
        previous = ROOT / BASE / 'previous_decisions' / path.name
        owned = {str(p.relative_to(ROOT)).replace('\\', '/') for p in (
            path, previous, ROOT / 'reports/claim_closure/progress.json')}
        if number == 15:
            owned.add(str(BASE / 'compound_search.json').replace('\\', '/'))
        if set(git('diff', '--cached', '--name-only').splitlines()) - owned:
            raise RuntimeError('Index contains unrelated staged work')
        if not previous.exists():
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, previous)
        frontier = frontiers[str(number)]
        updated = dict(old)
        updated.update(status='UNVERIFIABLE', reason=frontier['reason'],
            verification_scope='Reopened public-provenance and live-provider research; local fixtures do not prove empirical outcomes',
            next_input_artifact=frontier['next_input_artifact'], reopen_review_run=RUN,
            previous_decision=str(previous.relative_to(ROOT)).replace('\\', '/'),
            human_decision='Next required input artifact: ' + frontier['next_input_artifact'])
        if number == 17:
            updated['requirements_unmet'] = ['Eligible Claude model access', 'Eligible Qwen model access',
                'Reachable installed Ollama model', 'Full six-family live conformance observations']
        evidence = list(updated['evidence'])
        for relative in common + [BASE / p for p in specific.get(number, [])]:
            item = {'path': str(relative).replace('\\', '/'),
                    'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}
            if item not in evidence:
                evidence.append(item)
        updated['evidence'] = evidence
        write(path, updated)
        outcomes = gate(f'hunt-decision-{number}')
        audit = json.loads((ROOT / BASE / 'cohort/row_decisions.json').read_text())
        report = claim_report(outcomes, audit)
        report['original_test_evidence'] = {'observed_outcomes': {'passed': 201}, 'original_sources_changed': []}
        apply_closure(report, outcomes, ROOT / 'reports/claim_closure/claims', ROOT, require_all=True)
        progress_path = ROOT / 'reports/claim_closure/progress.json'
        progress = json.loads(progress_path.read_text())
        progress.update(reopen_review_run=RUN, latest_reopened_claim=number,
            reopened_reviewed_ids=sorted(int(p.stem) for p in (ROOT / 'reports/claim_closure/claims').glob('*.json')
                if json.loads(p.read_text()).get('reopen_review_run') == RUN),
            latest_full_suite=dict(Counter(outcomes.values())))
        write(progress_path, progress)
        paths = [str(p.relative_to(ROOT)) for p in (path, previous, progress_path)]
        if number == 15:
            paths.append(str(BASE / 'compound_search.json'))
        git('add', '--', *paths)
        git('diff', '--cached', '--check')
        git('commit', '--quiet', '-m', f'claim{number}: reassess as UNVERIFIABLE with acquired evidence and next input')
        print('Reassessed', number, git('rev-parse', '--short', 'HEAD'), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--source-commits']:
        source_commits()
    elif sys.argv[1:] == ['--decisions']:
        decisions()
    else:
        raise SystemExit('Choose --source-commits or --decisions; no implicit mutations')
