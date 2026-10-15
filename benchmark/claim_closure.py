"""Evidence-bound terminal decisions; UNVERIFIABLE never means disproven."""
import hashlib
import json
from collections import Counter
from pathlib import Path


def apply_closure(report, outcomes, directory, root, require_all=False):
    root = Path(root).resolve()
    claims = {row['id']:row for row in report['claims']}
    reviewed = set()
    for path in sorted(Path(directory).glob('*.json')):
        decision = json.loads(path.read_text(encoding='utf-8'))
        number = decision.get('id')
        if type(number) is not int or number not in claims or number in reviewed:
            raise ValueError('Invalid or duplicate closure claim identity')
        if decision.get('status') not in {'VERIFIED','UNVERIFIABLE'}:
            raise ValueError('Closure requires a terminal status')
        if not decision.get('reason') or not decision.get('verification_scope'):
            raise ValueError('Closure requires a reason and verification scope')
        if decision['status']=='UNVERIFIABLE' and not decision.get('requirements_unmet'):
            raise ValueError('UNVERIFIABLE requires specific unmet evidence requirements')
        evidence = decision.get('evidence')
        if not isinstance(evidence,list) or not evidence:
            raise ValueError('Closure requires hashed evidence')
        for artifact in evidence:
            target = (root/artifact['path']).resolve()
            if (not target.is_relative_to(root) or not target.is_file()
                    or target.name.startswith('.env') or '.git' in target.relative_to(root).parts):
                raise ValueError('Unsafe or missing closure evidence')
            if hashlib.sha256(target.read_bytes()).hexdigest()!=artifact.get('sha256'):
                raise ValueError('Closure evidence digest mismatch: '+artifact['path'])
        tests = decision.get('acceptance_tests') or []
        if decision['status']=='VERIFIED':
            if not tests:
                raise ValueError('VERIFIED requires behavior acceptance tests')
            for node in tests:
                observed = [value for key,value in outcomes.items()
                            if key==node or key.startswith(node+'[')]
                if not observed or any(value!='passed' for value in observed):
                    raise ValueError(f'Claim {number} acceptance is not passing: '+node)
            if claims[number].get('scope') in {'LOCAL','TOOLS'} and claims[number].get('local_proof')!='PASSED':
                raise ValueError(f'Claim {number} original acceptance is not passing')
            if number==2:
                original = report.get('original_test_evidence') or {}
                if (original.get('observed_outcomes')!={'passed':201}
                        or original.get('original_sources_changed')!=[]):
                    raise ValueError('Claim 2 requires all 201 unchanged original tests')
        claims[number].update(status=decision['status'],closure_reason=decision['reason'],
            verification_scope=decision['verification_scope'],
            unmet_requirements=decision.get('requirements_unmet',[]),
            human_decision=decision.get('human_decision'),closure_evidence=evidence,
            closure_acceptance_tests=tests,
            closure_decision_path=str(path.resolve().relative_to(root)).replace('\\','/'))
        reviewed.add(number)
    missing = sorted(set(claims)-reviewed)
    if require_all and missing:
        raise ValueError('Closure has unreviewed claims: '+str(missing))
    report['closure'] = {'reviewed':len(reviewed),'unreviewed_ids':missing,
        'complete':not missing,'statuses':dict(Counter(claims[number]['status'] for number in reviewed)),
        'semantics':'VERIFIED is limited to stated evidence scope; UNVERIFIABLE is an evidence gap in this run, not proof of impossibility.'}
    return report
