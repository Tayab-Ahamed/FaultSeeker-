import pytest


def test_two_accounts_from_one_security_publisher_are_not_independent():
    from scripts.review_source_consensus import publisher
    assert publisher('https://twitter.com/peckshield/status/123') == publisher('https://x.com/PeckShieldAlert/status/456')
    assert publisher('https://blocksec.com/blog/case') != publisher('https://www.certik.com/blog/case')
    assert publisher('https://blocksec.com.attacker.example/blog/case') is None


def test_model_suggestion_needs_real_quotes_and_cannot_create_transaction_identities():
    from scripts.review_source_consensus import validate_suggestion
    case = {'id':'case','candidate_hashes':['0x'+'a'*64],'sources':[
        {'publisher':'A','text':'The contract calls an untrusted external receiver before updating its balance and permits reentrancy.'},
        {'publisher':'B','text':'The reentrancy callback occurs before the balance update, allowing repeated withdrawals from the same deposit.'}]}
    suggestion = {'case_id':'case','vulnerability_class':'Reentrancy','reasoning':'Both sources describe state changes after external calls.',
                  'attack_transaction_hashes':['0x'+'a'*64], 'observations':[
                      {'publisher':s['publisher'],'quote':s['text']} for s in case['sources']]}
    assert validate_suggestion(suggestion,case)
    suggestion['attack_transaction_hashes'] = ['0x'+'b'*64]
    assert not validate_suggestion(suggestion,case)
    suggestion['attack_transaction_hashes'] = ['0x'+'a'*64]
    suggestion['observations'][0]['quote'] = 'An invented source quote with enough words to fool a length-only validator'
    assert not validate_suggestion(suggestion,case)


def test_annotation_proposals_can_use_explicitly_authorized_env_without_logging_key(tmp_path):
    from scripts.review_source_consensus import authorized_key
    local=tmp_path/'local.env'; alternate=tmp_path/'authorized.env'
    local.write_text('UNRELATED=value\n')
    alternate.write_text('BYNARA_API_KEY=private-test-value\n')
    assert authorized_key([local,alternate]) == 'private-test-value'
    local.write_text('NARAROUTER_API_KEY=local-test-value\n')
    assert authorized_key([local,alternate]) == 'local-test-value'


def test_review_cannot_accept_a_proposal_with_an_unbound_source_url():
    from scripts.review_source_consensus import validate_suggestion
    case={'id':'c','candidate_hashes':['tx'],'sources':[
        {'url':'https://one.example/report','publisher':'A','text':'One exact mechanistic quote with eight or more words here'},
        {'url':'https://two.example/report','publisher':'B','text':'Another exact mechanistic quote with eight or more words here'}]}
    suggestion={'case_id':'c','vulnerability_class':'Reentrancy','reasoning':'Agreement',
      'attack_transaction_hashes':['tx'],'observations':[
       {'publisher':s['publisher'],'url':'https://invented.example/report','quote':s['text']} for s in case['sources']]}
    assert not validate_suggestion(suggestion,case)


def test_unreviewed_model_proposal_cannot_be_materialized_as_ground_truth():
    from scripts.adjudicate_public_sources import reviewed_annotation
    with pytest.raises(ValueError,match='explicit'):
        reviewed_annotation({'consensus':True}, {}, {'chain':'eth','txn_hash':'tx'})


def test_source_review_is_bound_to_chain_as_well_as_transaction_hash():
    from scripts.adjudicate_public_sources import reviewed_annotation
    review={'decision':'APPROVE_SOURCE_CONSENSUS','reviewed_by':'Codex','chain':'fantom',
            'attack_transaction_hashes':['tx']}
    with pytest.raises(ValueError,match='chain'):
        reviewed_annotation(review,{}, {'chain':'eth','txn_hash':'tx'})


def test_independent_security_publisher_inventory_includes_original_incident_outlets():
    from scripts.review_source_consensus import publisher
    assert publisher('https://rekt.news/incident-rekt/') == 'Rekt'
    assert publisher('https://www.numencyber.com/incident/') == 'NumenCyber'
    assert publisher('https://blog.openzeppelin.com/incident') == 'OpenZeppelin'
    assert publisher('https://blog.openzeppelin.com.attacker.example/incident') is None
