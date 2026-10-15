"""Research integrity boundaries, exercised independently of paid providers."""
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import pytest


def test_public_fallbacks_cannot_embed_private_quicknode_path_credentials():
    from faultseeker.utils.rpc_provider import _PUBLIC
    assert all(not (urlsplit(url).hostname.endswith('.quiknode.pro') and urlsplit(url).path.strip('/'))
               for endpoints in _PUBLIC.values() for url, _weight in endpoints)


def _protocol():
    from benchmark import research_protocol
    return research_protocol


def test_names_and_titles_are_not_independent_annotations(tmp_path):
    p = _protocol()
    row = {'txn_hash': '0x' + 'a'*64, 'chain': 'eth', 'vuln_type': 'Reentrancy',
           'annotation': {'reviewers': ['Alice', 'Bob'], 'adjudicated_label': 'reentrancy'}}
    decision = p.admit(row, tmp_path)
    assert not decision['accepted']
    assert 'MISSING_INDEPENDENT_ANNOTATION_EVIDENCE' in decision['reasons']


def test_authorized_public_consensus_requires_matching_mechanistic_source_evidence(tmp_path):
    p = _protocol()
    tx = '0x'+'a'*64
    a = 'The price oracle trusts the current pool balances, allowing a flash loan to corrupt the quote.'
    b = 'Manipulating pool reserves during a flash loan inflates the oracle price and permits excess borrowing.'
    sources = []
    observations = []
    for i, excerpt in enumerate((a,b)):
        path = tmp_path/f'publisher{i}.txt'
        path.write_text(excerpt)
        bound = p.bind(path,tmp_path)
        sources.append({'publisher_id':f'publisher{i}','independence_group':f'publisher{i}',
            'artifact':bound,'review_status':'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED',
            'independence_basis':'Separate organizations, each describing their own analysis',
            'identity_basis':tx})
        observations.append({'publisher_id':f'publisher{i}','source_artifact':bound,
            'vulnerability_class':'Oracle price manipulation','mechanism_excerpt':excerpt})
    annotation = {'mode':'public-source-consensus-v1','adjudication_author':'Codex',
        'txn_hash':tx,'chain':'eth','is_exploit':True,'vuln_type':'Oracle price manipulation',
        'adjudication_basis':'Both sources identify a manipulable spot-balance oracle; the flash loan is financing, not the root cause.',
        'independent_observations':observations,'uncategorized':True}
    p.write_json(tmp_path/'annotation.json',annotation)
    row = {'txn_hash':tx,'chain':'eth','sources':sources,'annotation_record':p.bind(tmp_path/'annotation.json',tmp_path)}
    assert p.admit(row,tmp_path)['annotation_verified']
    annotation['independent_observations'][1]['mechanism_excerpt'] = 'An invented mechanism not in the publisher document'
    p.write_json(tmp_path/'annotation.json',annotation)
    row['annotation_record'] = p.bind(tmp_path/'annotation.json',tmp_path)
    assert not p.admit(row,tmp_path)['annotation_verified']


def test_rpc_success_is_not_an_exploit_label(tmp_path):
    p = _protocol()
    tx = '0x' + 'a'*64
    record = {'txn_hash': tx, 'chain': 'eth', 'chain_id': 1, 'mode': 'live-rpc',
              'transaction': {'hash': tx, 'chainId': '0x1', 'blockHash': '0x'+'b'*64},
              'receipt': {'transactionHash': tx, 'blockHash': '0x'+'b'*64, 'status': '0x1'}}
    p.write_json(tmp_path/'rpc.json', record)
    result = p.admit({'txn_hash': tx, 'chain': 'eth', 'rpc': p.bind(tmp_path/'rpc.json', tmp_path)}, tmp_path)
    assert result['rpc_identity_verified']
    assert not result['accepted']


def test_artifact_tampering_cannot_be_admitted(tmp_path):
    p = _protocol()
    p.write_json(tmp_path/'rpc.json', {'state': 'original'})
    binding = p.bind(tmp_path/'rpc.json', tmp_path)
    p.write_json(tmp_path/'rpc.json', {'state': 'changed'})
    with pytest.raises(ValueError, match='digest'):
        p.read_bound(binding, tmp_path)


def test_empty_split_does_not_consume_final_exam(tmp_path):
    p = _protocol()
    split = p.make_split([], 'a'*64, seed=1729)
    assert split['status'] == 'BLOCKED_NO_ACCEPTED_DATA'
    with pytest.raises(ValueError, match='partition'):
        p.claim_exam(tmp_path/'exam.json', split, 'b'*64)
    assert not (tmp_path/'exam.json').exists()


def test_stratified_split_is_deterministic_disjoint_and_groups_incidents():
    p = _protocol()
    rows = [{'txn_hash': '0x'+format(i, '064x'), 'chain': 'eth' if i<10 else 'bsc',
             'complexity_class': 'Moderate', 'incident_id': 'incident-'+str(i//2)} for i in range(20)]
    first = p.make_split(rows, 'a'*64, seed=1729)
    second = p.make_split(list(reversed(rows)), 'a'*64, seed=1729)
    assert first == second
    assert first['status'] == 'FROZEN'
    assert len(first['train_ids']) == 14
    assert len(first['heldout_ids']) == 6
    assert not set(first['train_ids']) & set(first['heldout_ids'])
    for i in range(0,20,2):
        assert (p.identity(rows[i]) in first['train_ids']) == (p.identity(rows[i+1]) in first['train_ids'])


def test_training_loader_never_opens_heldout_partition(tmp_path):
    p = _protocol()
    p.write_json(tmp_path/'train.json', [{'txn_hash':'0x'+'a'*64,'chain':'eth'}])
    split = {'status':'FROZEN','train_ids':['eth:0x'+'a'*64],
             'heldout_ids':['eth:0x'+'b'*64], 'partitions':{
                 'train': p.bind(tmp_path/'train.json',tmp_path),
                 'heldout': {'path':'DOES_NOT_EXIST.json','sha256':'0'*64}}}
    assert p.load_train(split,tmp_path)[0]['txn_hash'] == '0x'+'a'*64


def test_final_exam_claim_is_atomic_and_cannot_be_repeated(tmp_path):
    p = _protocol()
    split = {'status':'FROZEN','train_ids':['train'], 'heldout_ids':['heldout'], 'manifest_sha256':'a'*64}
    def claim(_):
        try:
            p.claim_exam(tmp_path/'exam.json', split, 'b'*64)
            return 'claimed'
        except FileExistsError:
            return 'already-consumed'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim,range(2)))
    assert sorted(results) == ['already-consumed','claimed']


def test_experiment_log_rejects_heldout_members_and_zero_sample_scores(tmp_path):
    p = _protocol()
    split = {'status':'FROZEN','train_ids':['train'],'heldout_ids':['heldout']}
    with pytest.raises(ValueError, match='train'):
        p.append_experiment(tmp_path/'experiments_log.json', split,
            {'kind':'scored-train','sample_ids':['heldout'],'metrics':{'f1':1.0},'seed':1729,'config':{}})
    with pytest.raises(ValueError, match='empty'):
        p.append_experiment(tmp_path/'experiments_log.json', split,
            {'kind':'scored-train','sample_ids':[],'metrics':{'f1':1.0},'seed':1729,'config':{}})
    p.append_experiment(tmp_path/'experiments_log.json', split,
        {'kind':'blocked-preflight','sample_ids':[],'metrics':None,'seed':1729,'config':{},'reason':'no data'})
    assert json.loads((tmp_path/'experiments_log.json').read_text())[0]['metrics'] is None
