import hashlib
import json

import pytest


def fixture_decision(tmp_path,status='UNVERIFIABLE'):
    artifact = tmp_path/'evidence.json';artifact.write_text('{"observed":true}')
    decision = {'id':3,'status':status,'reason':'Independent annotations are absent',
        'verification_scope':'current evidence only','requirements_unmet':['two independent annotators'],
        'acceptance_tests':[], 'evidence':[{'path':'evidence.json',
            'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
    directory = tmp_path/'decisions';directory.mkdir()
    (directory/'03.json').write_text(json.dumps(decision))
    return directory,artifact


def test_closure_requires_hashed_evidence_and_explicit_reason(tmp_path):
    from benchmark.claim_closure import apply_closure
    directory,artifact = fixture_decision(tmp_path)
    report = {'claims':[{'id':3,'status':'BLOCKED-BY-DATA','scope':'DATA'}]}
    apply_closure(report,{},directory,tmp_path)
    assert report['claims'][0]['status']=='UNVERIFIABLE'
    artifact.write_text('changed')
    with pytest.raises(ValueError,match='digest'):
        apply_closure(report,{},directory,tmp_path)


def test_verified_closure_requires_passing_behavior_acceptance(tmp_path):
    from benchmark.claim_closure import apply_closure
    directory,_ = fixture_decision(tmp_path,'VERIFIED')
    p=directory/'03.json';d=json.loads(p.read_text());d['acceptance_tests']=['real-test'];p.write_text(json.dumps(d))
    report={'claims':[{'id':3,'status':'BLOCKED-BY-DATA','scope':'DATA'}]}
    with pytest.raises(ValueError,match='acceptance'):
        apply_closure(report,{'real-test':'skipped'},directory,tmp_path)


def test_strict_closure_does_not_hide_unreviewed_claims(tmp_path):
    from benchmark.claim_closure import apply_closure
    directory,_ = fixture_decision(tmp_path)
    report={'claims':[{'id':i,'status':'PENDING','scope':'DATA'} for i in range(1,32)]}
    with pytest.raises(ValueError,match='unreviewed'):
        apply_closure(report,{},directory,tmp_path,require_all=True)


def test_publication_snapshot_is_public_and_open_licensed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'reports/claim_closure/sources'
    metadata=json.loads((root/'public_repository.json').read_text())
    assert metadata['private'] is False
    assert metadata['license']['spdx_id']=='Apache-2.0'
    assert 'Apache License' in (root/'public_repository_LICENSE.txt').read_text()
