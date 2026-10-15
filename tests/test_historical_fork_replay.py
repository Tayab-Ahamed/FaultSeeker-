"""Opt-in live archive replay plus offline safety checks."""
import os
import json
from pathlib import Path

import pytest
from dotenv import dotenv_values


@pytest.mark.parametrize('kind', [0, 2])
def test_signed_transaction_reconstruction_preserves_hash(kind):
    from eth_account import Account
    from scripts.replay_historical_opcodes import signed_transaction
    transaction = {'nonce': 0, 'gas': 21000, 'to': '0x' + '11' * 20,
                   'value': 123, 'data': '0x', 'chainId': 1}
    if kind == 2:
        transaction.update(type=2, maxFeePerGas=100, maxPriorityFeePerGas=1, accessList=[])
    else:
        transaction['gasPrice'] = 100
    signed = Account.sign_transaction(transaction, bytes.fromhex('01' * 32))
    canonical = dict(transaction, input=transaction['data'], v=signed.v,
                     r=signed.r, s=signed.s, hash='0x' + signed.hash.hex().removeprefix('0x'))
    assert signed_transaction(canonical) == '0x' + signed.raw_transaction.hex().removeprefix('0x')


def test_replay_rejects_receipt_changes():
    from scripts.replay_historical_opcodes import verify_receipt
    receipt = {'transactionHash': '0xabc', 'status': '0x1', 'gasUsed': '0x5208',
               'transactionIndex': '0x0', 'contractAddress': None, 'logs': []}
    verify_receipt(receipt, dict(receipt))
    with pytest.raises(ValueError, match='gasUsed'):
        verify_receipt(receipt, dict(receipt, gasUsed='0x5209'))


def test_rpc_meter_refuses_requests_above_limit(tmp_path):
    from scripts.replay_historical_opcodes import MeteredRPC
    meter = MeteredRPC('https://unused.invalid', tmp_path / 'meter.json', max_requests=0)
    with pytest.raises(RuntimeError, match='request limit'):
        meter.forward({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_chainId', 'params': []})
    assert meter.count == 0


def test_archive_proxy_cannot_broadcast_to_mainnet(tmp_path):
    from scripts.replay_historical_opcodes import MeteredRPC
    meter = MeteredRPC('https://unused.invalid', tmp_path / 'meter.json')
    with pytest.raises(ValueError, match='read RPC'):
        meter.forward({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_sendRawTransaction', 'params': ['0x00']})
    assert meter.count == 0


def test_mining_can_use_a_separately_bounded_timeout(monkeypatch):
    import io
    from scripts import replay_historical_opcodes as runner
    observed = []
    def respond(_request, timeout):
        observed.append(timeout)
        return io.BytesIO(b'{"result":"0x0"}')
    monkeypatch.setattr(runner, 'urlopen', respond)
    assert runner.local_rpc('http://127.0.0.1:1', 'evm_mine', [], timeout_seconds=600) == '0x0'
    assert observed == [600]
    with pytest.raises(ValueError, match='bounded'):
        runner.local_rpc('http://127.0.0.1:1', 'evm_mine', [], timeout_seconds=0)


def test_pre_metering_rpc_estimate_is_accounted_exactly_once(tmp_path):
    from scripts.replay_historical_opcodes import account_prior_requests, MeteredRPC
    meter = MeteredRPC('https://unused.invalid', tmp_path / 'ledger.json')
    account_prior_requests(meter.guard, 7)
    account_prior_requests(meter.guard, 7)
    assert meter.guard.report()['spent_usd'] == pytest.approx(0.000042)


def test_recorded_historical_capture_validates_storage_and_receipt():
    from scripts.replay_historical_opcodes import validate_recorded_capture, REENTRANT
    path = Path(__file__).resolve().parents[1] / 'reports/historical_replay' / (REENTRANT + '.json.gz')
    proof = validate_recorded_capture(path, REENTRANT)
    assert proof['sload_count'] == 80
    assert proof['sstore_count'] == 29
    assert proof['storage_owners_verified'] is True
    manifest = json.loads((path.parent / 'final_accounting.json').read_text())
    assert proof['artifact_sha256'] == manifest['capture_proof']['artifact_sha256']


def test_recorded_comparison_capture_validates_storage_and_receipt():
    from scripts.replay_historical_opcodes import validate_recorded_capture, COMPARISON
    directory = Path(__file__).resolve().parents[1] / 'reports/claim_closure/comparison_attempt_2'
    proof = validate_recorded_capture(directory/(COMPARISON+'.json.gz'),COMPARISON)
    manifest = json.loads((directory/'historical_replay_summary.json').read_text())
    assert proof['sload_count'] == 8
    assert proof['sstore_count'] == 2
    assert proof['artifact_sha256'] == manifest['cases'][0]['artifact_sha256']


def test_historical_fork_captures_reentrant_storage(tmp_path, monkeypatch):
    values = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
    if not (os.getenv('DRPC_RPC_URL') or values.get('DRPC_RPC_URL')):
        pytest.skip('DRPC_RPC_URL unset: historical replay requires archive access')
    if os.getenv('FAULTSEEKER_RUN_HISTORICAL_REPLAY') != '1':
        pytest.skip('Set FAULTSEEKER_RUN_HISTORICAL_REPLAY=1 to permit counted live RPC')
    # Real paid calls must not use conftest's simulated-usage ledger.
    monkeypatch.setenv('FAULTSEEKER_SPEND_LEDGER', str(
        Path(__file__).resolve().parents[1] / 'data/research/spend_ledger.json'))
    from scripts.replay_historical_opcodes import run
    report = run(output=tmp_path, transaction_hashes=[
        '0xd4fafa1261f6e4f9c8543228a67caf9d02811e4ad3058a2714323964a8db61f6'],
        max_requests=2000)
    assert report['status'] == 'CAPTURED'
    case = report['cases'][0]
    assert case['sload_count'] > 0
    assert case['sstore_count'] > 0
    assert case['normalization_complete'] is True
    assert case['storage_owners_verified'] is True
    assert case['receipt_matches'] is True
