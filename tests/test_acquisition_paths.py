import pytest
from benchmark.acquire_paper_evidence import capture_transaction
from faultseeker.utils.waf_recovery import RecoveryClient, recovery_metrics
from faultseeker.utils.rpc_provider import _build_providers


def test_drpc_key_and_chain_endpoint_are_used_without_live_requests(monkeypatch):
    monkeypatch.setenv('DRPC_API_KEY', 'fixture-key')
    monkeypatch.setenv('DRPC_RPC_URL', 'https://example.test/{chain}?dkey={api_key}')
    urls = [provider.url for provider in _build_providers('eth')]
    assert 'https://example.test/eth?dkey=fixture-key' in urls


def test_capture_checks_chain_and_cross_provider_identity_before_writing(tmp_path):
    def rpc(url, method, params):
        return '0x38' if method == 'eth_chainId' else None
    with pytest.raises(ValueError, match='chain'):
        capture_transaction('0x'+'a'*64, 'eth', ['https://a.test','https://b.test'], tmp_path, rpc=rpc)
    assert not list(tmp_path.glob('*.json'))


def test_challenge_recovery_records_every_attempt_and_real_denominator():
    replies = iter([(403, 'Just a moment... cf-chl-test'), (200, '<html>transaction data</html>')])
    client = RecoveryClient(transport=lambda url, strategy: next(replies), strategies=['standard','browser'])
    result = client.fetch('https://explorer.example/tx/one')
    assert result['recovered'] is True
    assert len(result['attempts']) == 2
    assert result['attempts'][0]['challenge'] is True
    metrics = recovery_metrics([result, {'challenged': False,'recovered': False,'attempts': []}])
    assert metrics['challenged_requests'] == 1
    assert metrics['recovered_requests'] == 1
    assert metrics['bypass_fraction'] == 1


def test_ordinary_failure_is_not_relabelled_as_challenge_success():
    client = RecoveryClient(transport=lambda *args: (500, 'server error'), strategies=['standard'])
    result = client.fetch('https://explorer.example/tx/one')
    metrics = recovery_metrics([result])
    assert metrics['challenged_requests'] == 0
    assert metrics['bypass_fraction'] is None


def test_production_collector_runs_recovery_and_retains_attempt_evidence():
    from faultseeker.data_collection.txn_info_collector import TransactionInfoCollector
    replies = iter([(403,'cf-chl-test'),(200,'actual fixture response')])
    collector = TransactionInfoCollector(RecoveryClient(transport=lambda *a: next(replies),
                                                       strategies=['standard','browser']))
    assert collector._fetch_website_content('https://explorer.example/tx/one') == 'actual fixture response'
    assert collector.last_fetch_evidence['recovered'] is True
    assert len(collector.last_fetch_evidence['attempts']) == 2


def test_provider_stats_do_not_expose_rpc_credentials(monkeypatch, capsys):
    from faultseeker.utils import rpc_provider
    provider = rpc_provider._RPCProvider('https://user:password@rpc.example/secretpath?dkey=secretkey')
    monkeypatch.setattr(rpc_provider._registry,'sorted_providers',lambda chain:[provider])
    rpc_provider.print_provider_stats('eth')
    output = capsys.readouterr().out
    assert all(secret not in output for secret in ('password','secretpath','secretkey'))
