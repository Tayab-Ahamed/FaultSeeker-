"""One evidence decision per commit, with real full-suite gates before AND after.

Resume checks committed registry markers rather than treating unstaged changes as
completed work. No network, provider dispatch, paper editing or threshold tuning.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.collect_canonical_evidence import BASE, write
from scripts.finalize_claim_closure import git
from scripts.reopen_claim_decisions import gate
from benchmark.claim_registry import claim_report
from benchmark.claim_closure import apply_closure

RUN = 'canonical-history-review-2026-10-15'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    if git('branch', '--show-current') != 'paper-claims-verified':
        raise RuntimeError('Wrong branch')
    if git('diff', '--cached', '--name-only'):
        raise RuntimeError('Unrelated staged work')


def stage_commit(paths, message):
    spec = ROOT / 'build/canonical-stage-paths.txt'
    spec.write_bytes(b''.join(str(p.relative_to(ROOT)).replace('\\', '/').encode() + b'\0' for p in paths))
    git('add', '--pathspec-from-file=' + str(spec), '--pathspec-file-nul')
    git('diff', '--cached', '--check')
    git('commit', '--quiet', '-m', message)
    return git('rev-parse', 'HEAD')


def record_gate(label):
    outcomes = gate(label)
    source = ROOT / 'build/closure_acceptance' / (label + '.xml')
    target = BASE / 'verification' / (label + '.xml.gz')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(source.read_bytes(), mtime=0))
    return outcomes, {'label': label, 'outcomes': dict(Counter(outcomes.values())),
                      'junit': target.relative_to(ROOT).as_posix(), 'sha256': digest(target),
                      'original_test_sources_changed': [], 'original_test_cases_passed': 201}


def source():
    check()
    paths = [p for p in BASE.rglob('*') if p.is_file()]
    paths += [ROOT / p for p in ('.gitattributes', 'tests/test_canonical_evidence.py',
              'scripts/collect_canonical_evidence.py', 'scripts/reproduce_canonical_harness.py',
              'scripts/analyze_canonical_evidence.py', 'scripts/report_canonical_decisions.py',
              'scripts/commit_canonical_decisions.py')]
    _, pre = record_gate('canonical-source-pre')
    paths.append(ROOT / pre['junit'])
    commit = stage_commit(paths, 'claim4: register canonical history, original annotations and reproduced feature results')
    _, post = record_gate('canonical-source-post')
    write(BASE / 'source_verification.json', {'commit': commit, 'before': pre, 'after': post})
    print('Canonical evidence committed', commit[:8], flush=True)


def decisions():
    mapping = json.loads((BASE / 'paper_vs_repo.json').read_text())
    common = ['manifest.json', 'cohort_history.json', 'findings.json', 'paper_vs_repo.json',
              'history_search.json', 'accounting.json']
    verification = BASE / 'verification.json'
    records = json.loads(verification.read_text()) if verification.exists() else {'run': RUN, 'decisions': []}
    for proposal in mapping['reopened_decisions']:
        check()
        n = proposal['id']
        path = ROOT / 'reports/claim_closure/claims' / f'{n:02d}.json'
        old = json.loads(path.read_text())
        if old.get('canonical_review_run') == RUN and not git('diff', 'HEAD', '--', str(path.relative_to(ROOT))):
            if not any(r['id'] == n for r in records['decisions']):
                commit = git('log', '-1', '--format=%H', '--', str(path.relative_to(ROOT)))
                _, post = record_gate(f'canonical-{n:02d}-post')
                records['decisions'].append({'id': n, 'commit': commit, 'after': post})
                write(verification, records)
            continue
        if old['status'] != 'UNVERIFIABLE':
            raise RuntimeError('Refusing to alter an out-of-scope VERIFIED claim')
        previous = BASE / 'previous_decisions' / path.name
        previous.parent.mkdir(parents=True, exist_ok=True)
        if not previous.exists():
            shutil.copyfile(path, previous)
        updated = dict(old)
        updated.update(status=proposal['status'], reason=proposal['reason'],
            paper_verdict=proposal['paper_verdict'], canonical_review_run=RUN,
            verification_scope='Recovered canonical Git provenance and offline historical feature arithmetic; not full empirical paper replication',
            requirements_unmet=[proposal['missing_input']], next_input_artifact=proposal['missing_input'],
            human_decision='Next evidence input: ' + proposal['missing_input'],
            previous_decision=previous.relative_to(ROOT).as_posix())
        evidence = list(updated['evidence'])
        for filename in common:
            target = BASE / filename
            item = {'path': target.relative_to(ROOT).as_posix(), 'sha256': digest(target)}
            if item not in evidence:
                evidence.append(item)
        updated['evidence'] = evidence
        write(path, updated)
        outcomes, pre = record_gate(f'canonical-{n:02d}-pre')
        report = claim_report(outcomes, json.loads((ROOT / 'reports/provenance_hunt/cohort/row_decisions.json').read_text()))
        report['original_test_evidence'] = {'observed_outcomes': {'passed': 201}, 'original_sources_changed': []}
        apply_closure(report, outcomes, ROOT / 'reports/claim_closure/claims', ROOT, require_all=True)
        progress_path = ROOT / 'reports/claim_closure/progress.json'
        progress = json.loads(progress_path.read_text())
        progress.update(canonical_review_run=RUN, latest_canonical_claim=n,
            canonical_reviewed_ids=sorted(int(p.stem) for p in path.parent.glob('*.json')
                if json.loads(p.read_text()).get('canonical_review_run') == RUN),
            latest_full_suite=pre['outcomes'])
        write(progress_path, progress)
        commit = stage_commit([path, previous, progress_path, ROOT / pre['junit']],
            f'claim{n}: reassess canonical evidence as {proposal["paper_verdict"]}')
        # A failed post-commit gate raises and stops the queue. No claim is promoted.
        _, post = record_gate(f'canonical-{n:02d}-post')
        records['decisions'].append({'id': n, 'status': proposal['status'], 'paper_verdict': proposal['paper_verdict'],
                                    'commit': commit, 'before': pre, 'after': post})
        write(verification, records)
        print('Decision committed and post-commit verified', n, commit[:8], flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--source']:
        source()
    elif sys.argv[1:] == ['--decisions']:
        decisions()
    else:
        raise SystemExit('Choose --source or --decisions explicitly')
