import hashlib


def test_exact_hash_in_url_or_challenge_is_not_incident_corroboration(tmp_path):
    from scripts.hunt_claim_provenance import inspect_artifact
    tx = '0x' + 'ab' * 32
    page = tmp_path / 'page'
    page.write_text('Just a moment... Enable JavaScript and cookies to continue')
    result = inspect_artifact(tx, {'url': 'https://etherscan.io/tx/' + tx,
        'file': str(page), 'sha256': hashlib.sha256(page.read_bytes()).hexdigest(), 'http_status': 200})
    assert result['body_hash_match'] is False
    assert result['usable_identity_reference'] is False


def test_optimism_explorer_is_not_ethereum_mainnet():
    from scripts.hunt_claim_provenance import ethereum_transaction_link
    tx = '0x' + 'ab' * 32
    assert ethereum_transaction_link('https://etherscan.io/tx/' + tx) == tx
    assert ethereum_transaction_link('https://optimistic.etherscan.io/tx/' + tx) is None


def test_explorer_echo_of_unknown_hash_is_rejected(tmp_path):
    from scripts.hunt_claim_provenance import inspect_artifact
    tx = '0x' + 'cd' * 32
    page = tmp_path / 'page'
    page.write_text('Transaction ' + tx + ': Sorry, we are unable to locate this transaction hash')
    result = inspect_artifact(tx, {'url': 'https://etherscan.io/tx/' + tx,
        'file': str(page), 'sha256': hashlib.sha256(page.read_bytes()).hexdigest(), 'http_status': 200})
    assert result['body_hash_match'] is True
    assert result['usable_identity_reference'] is False
