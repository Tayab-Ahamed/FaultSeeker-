"""Offline local acceptance plus a complete, fail-closed paper claim ledger."""
import argparse
import json
import os
import platform
import hashlib
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmark.claim_registry import claim_report
from benchmark.evidence_manifest import audit_dataset, digest_file


class TestEvidence:
    def __init__(self):
        self.outcomes = {}

    def pytest_runtest_logreport(self, report):
        node = report.nodeid.replace('\\', '/')
        if report.when == 'call' or report.failed:
            self.outcomes[node] = report.outcome


def _git(*arguments):
    try:
        result = subprocess.run(['git',*arguments],cwd=ROOT,capture_output=True,text=True,timeout=10)
        return result.stdout.strip() if result.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):
        return None


def attach_commit_provenance(report):
    commits = {}
    for line in (_git('log','--format=%H\t%s') or '').splitlines():
        revision,_,subject = line.partition('\t')
        match = re.search(r'\(claim-(\d+)\)',subject)
        if match:
            commits.setdefault(int(match.group(1)),revision)
    dependencies = {1:[31],4:[3,27],5:[13],6:[13,3],7:[13,3],8:[13,3],9:[9,26,10],
        10:[10,9],11:[11,10,9],12:[12,10,9],14:[13],15:[22,27,13],17:[16],
        18:[18,16,13],19:[19,26],20:[20,19],21:[20,13],22:[22,16],24:[24,20,22],
        25:[25,26,27],26:[26,9],28:[13],29:[13,24]}
    for claim in report['claims']:
        claim['claim_commit'] = commits.get(claim['id'])
        claim['implementation_commits'] = [commits[number] for number in dependencies.get(claim['id'],[claim['id']])
                                           if number in commits]


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/'claim_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# Local paper claim verification', '',
             'Local acceptance tests do not establish empirical paper outcomes.', '',
             f"Suite exit code: {report['test_exit_code']}; test outcomes: {report['test_counts']}.", '',
             'Each commit below passed the accumulated suite in an isolated staged snapshot before commit.', '',
             '| Claim | Status | Local proof | Implementation commits | Acceptance tests | Missing external evidence |',
             '|---|---|---|---|---|---|']
    for row in report['claims']:
        requirement = row['required_evidence']
        if row['required_env']:
            requirement += ' Environment: ' + ', '.join(row['required_env'])
        commits = ', '.join(value[:12] for value in row.get('implementation_commits',[])) or 'Publication/data evidence pending'
        tests = '<br>'.join('`'+node+'`' for node in row['tests']) or 'Public release is outside this local run'
        lines.append(f"| {row['id']}. {row['claim']} | {row['status']} | {row['local_proof']} | {commits} | {tests} | {requirement} |")
    lines += ['', 'Original test evidence: `'+json.dumps(report['original_test_evidence'],sort_keys=True)+'`.']
    lines += ['', '## Data evidence', '',
              f"Accepted {report['dataset_audit']['accepted_rows']} of {report['dataset_audit']['input_rows']} input rows.",
              'Missing evidence counts: `' + json.dumps(report['dataset_audit']['missing_counts'], sort_keys=True) + '`.',
              '', '## Numerical constraints', '',
              '- Published percentages remain targets for experiments; the paper is unchanged.',
              '- Every confusion matrix reports integer TP/FP/FN/TN and denominator.',
              '- Twenty single binary outcomes have 5 percentage point accuracy steps; 68% and 81% require a different explicit aggregation.',
              '- $0.039 versus $0.060 is 35% savings. Measure the actual paired baseline before claiming 58%.',
              '- No authentic cohort rows, query outcomes or traces are synthesized to meet a target.',
              '- The .80 structural cap equals the .80 CONFIRMED label boundary; fallback context remains explicit and is not storage proof.',
              '', 'Kluster is waived for local development only. Re-enable repository rules before PR or push.']
    (output/'claim_report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT/'benchmark/benchmark_classification_fixed.csv')
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/local_verification')
    parser.add_argument('--require-paper-verification', action='store_true')
    args = parser.parse_args(argv)
    if os.name == 'nt':
        sys.modules.setdefault('readline',None)
    import pytest
    plugin = TestEvidence()
    code = int(pytest.main([str(ROOT/'tests'), '-q', '--junitxml='+str(args.output/'tests.xml')], plugins=[plugin]))
    audit = audit_dataset(args.dataset, args.evidence_root, target=246)
    report = claim_report(plugin.outcomes, audit)
    baseline = json.loads((ROOT/'benchmark/baseline_tests.json').read_text(encoding='utf-8-sig'))
    baseline_files = baseline['source_sha256']
    original = {node:outcome for node,outcome in plugin.outcomes.items() if node.split('::')[0] in baseline_files}
    changed = []
    for name,digest in baseline_files.items():
        path = (ROOT/name).resolve()
        if (not path.is_relative_to(ROOT) or not path.is_file()
                or hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest() != digest):
            changed.append(name)
    report['original_test_evidence'] = {'expected_baseline_count':201,'observed_outcomes':dict(Counter(original.values())),
        'original_sources_changed':changed,'baseline_commit':baseline['baseline_commit']}
    if len(original) != 201 or any(value != 'passed' for value in original.values()) or report['original_test_evidence']['original_sources_changed']:
        row = next(row for row in report['claims'] if row['id']==2)
        row.update(status='LOCAL-ACCEPTANCE-PENDING',local_proof='FAILED-OR-MISSING')
    attach_commit_provenance(report)
    report.update(test_exit_code=code, test_counts=dict(Counter(plugin.outcomes.values())),
                  timestamp=datetime.now(timezone.utc).isoformat(), python_version=platform.python_version(),
                  revision=_git('rev-parse','HEAD'),
                  test_manifest_sha256={str(p.relative_to(ROOT)): digest_file(p) for p in sorted((ROOT/'tests').glob('test_*.py'))})
    write_report(report, args.output)
    print(f'Claim report: {args.output / "claim_report.md"}')
    if code:
        return code
    if args.require_paper_verification and any(r['status'] != 'VERIFIED' for r in report['claims']):
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
