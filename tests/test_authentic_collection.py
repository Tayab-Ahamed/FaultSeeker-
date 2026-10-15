from urllib.parse import urlsplit

import pytest


def test_explorer_host_exactness_prevents_cross_chain_substring_errors():
    from scripts.rebuild_authentic_cohort import extract_candidates
    a, b = '0x'+'a'*64, '0x'+'b'*64
    text = f'### 20220315 - Event\nhttps://gnosisscan.io/tx/{a}\nhttps://ftmscan.com/tx/{b}\nhttps://notetherscan.io/tx/{a}'
    rows = extract_candidates(text, 'https://example.org/index')
    assert {(r['chain'],r['txn_hash']) for r in rows} == {('gnosis',a),('fantom',b)}
    assert all(not r.get('annotation_record') and not r.get('vuln_type') for r in rows)


def test_poc_imports_are_transaction_leads_and_never_title_based_annotations():
    from scripts.rebuild_authentic_cohort import import_poc_leads
    a = '0x'+'c'*64
    existing = [{'txn_hash':a,'chain':'eth'}]
    imported = [{'candidate_tx_hash':a,'candidate_chain':'eth','title':'duplicate'},
                {'candidate_tx_hash':'0x'+'d'*64,'candidate_chain':'gnosis',
                 'title':'Reentrancy','incident_id':'event','source':'https://example.org/poc'},
                {'candidate_tx_hash':'bad','candidate_chain':'eth','title':'bad'}]
    result = import_poc_leads(existing,imported)
    assert len(result)==2
    assert result[-1]['chain']=='gnosis'
    assert 'vuln_type' not in result[-1] and 'annotation_record' not in result[-1]


def test_drpc_url_routing_preserves_authorized_key_without_copying_wrong_chain():
    from scripts.rebuild_authentic_cohort import drpc_url
    result = drpc_url('https://lb.drpc.live/ethereum/TEST-NOT-A-KEY', 'gnosis')
    assert urlsplit(result).path == '/gnosis/TEST-NOT-A-KEY'
    with pytest.raises(ValueError):
        drpc_url('https://other.example/api/TEST-NOT-A-KEY','gnosis')


def test_rpc_response_ids_and_identity_are_bound_to_requested_chain():
    from scripts.rebuild_authentic_cohort import identity_observation
    tx, block = '0x'+'a'*64, '0x'+'b'*64
    payload = [{'id':2,'result':{'transactionHash':tx,'blockHash':block,'status':'0x1'}},
               {'id':1,'result':{'hash':tx,'blockHash':block,'chainId':'0x64'}}]
    result = identity_observation({'txn_hash':tx,'chain':'gnosis'},100,payload)
    assert result['identity_receipt_match']
    wrong = identity_observation({'txn_hash':tx,'chain':'eth'},1,payload)
    assert not wrong['identity_receipt_match']


def test_legacy_transaction_chain_is_derived_from_eip155_signature_not_assumed():
    from benchmark.research_protocol import transaction_chain_id
    assert transaction_chain_id({'type':'0x0','v':'0x217'}) == 250
    assert transaction_chain_id({'type':'0x0','v':'0x218'}) == 250
    with pytest.raises(ValueError):
        transaction_chain_id({'type':'0x0','v':'0x1b'})
    with pytest.raises(ValueError):
        transaction_chain_id({'type':'0x2','v':'0x217'})
    with pytest.raises(ValueError):
        transaction_chain_id({'chainId':'0x1','type':'0x0','v':'0x217'})
