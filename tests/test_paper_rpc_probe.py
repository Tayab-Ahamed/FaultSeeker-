import pytest


def test_capability_probe_records_rejection_without_echoing_exception():
    from scripts.probe_paper_rpc import observe
    class RPC:
        def forward(self, _payload):
            raise RuntimeError('secret-token-in-provider-url')
    result = observe(RPC(), 'debug_traceTransaction', [], 'opcode')
    assert result['status'] == 'REQUEST-FAILED'
    assert 'secret-token' not in str(result)


def test_capability_probe_does_not_promote_rpc_error_to_support():
    from scripts.probe_paper_rpc import observe
    class RPC:
        def forward(self, _payload):
            return {'error': {'code': -32602, 'message': 'bad options'}}
    result = observe(RPC(), 'debug_traceTransaction', [], 'opcode')
    assert result['status'] == 'RPC-REJECTED'
    assert result['rpc_code'] == -32602


def test_archive_proxy_allows_trace_reads_but_still_denies_broadcast(tmp_path):
    from scripts.replay_historical_opcodes import READ_METHODS, MeteredRPC
    assert {'debug_traceTransaction', 'trace_replayTransaction', 'eth_call', 'eth_getLogs'} <= READ_METHODS
    meter = MeteredRPC('https://unused.invalid', tmp_path/'budget.json')
    with pytest.raises(ValueError, match='read RPC'):
        meter.forward({'method':'eth_sendRawTransaction', 'params':['0x00']})
