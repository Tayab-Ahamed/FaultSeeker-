"""Transport failures must remain observable and stop paid-role recovery."""
import inspect
import json

import pytest

from benchmark import nara_pilot_provider as provider
import faultseeker.core.llm_router as router_module
from faultseeker.core.llm_router import HybridLLMRouter
from faultseeker.core.spend_guard import SpendGuard


def test_default_transport_uses_isolated_deadline_worker():
    transport = inspect.signature(provider.NaraPilot).parameters['transport'].default
    assert transport.__module__ == 'benchmark.nara_http_transport'
    assert transport is provider.http_transport


def test_failed_transport_records_elapsed_duration_and_settles_once(tmp_path, monkeypatch):
    pricing = {provider.MODEL: {'input': 0.1, 'output': 0.2}}
    monkeypatch.setitem(router_module.COST_RATES, provider.MODEL, pricing[provider.MODEL])
    guard = SpendGuard(tmp_path / 'accounting.json', pricing=pricing)
    router = HybridLLMRouter(cloud_model=provider.MODEL, routing_strategy='cloud-only',
                            remote_model_ids=[provider.MODEL], spend_guard=guard)
    now = [10.0]
    attempts = []

    def timeout(url, headers, body, seconds):
        attempts.append(body)
        now[0] += 1.25
        raise TimeoutError('credential-bearing arbitrary message must not persist')

    pilot = provider.NaraPilot(api_key='nonsecret-test-credential', router=router,
                               output_dir=tmp_path / 'calls', transport=timeout,
                               clock=lambda: now[0])
    agent = pilot.factory('system', 'processing_agent')
    with pytest.raises(ValueError, match='TimeoutError'):
        agent.query('public trace')
    with pytest.raises(provider.StudyStop):
        pilot.factory('system', 'generation_agent').query('no recovery dispatch')

    assert len(attempts) == pilot.calls == 1
    events = guard.report()['events']
    assert [event['event'] for event in events] == ['reserve', 'settle']
    assert events[0]['id'] == events[1]['id']
    assert events[1]['failed'] is True
    assert events[1]['usage_source'] == 'reservation'
    assert events[1]['amount_usd'] == events[0]['amount_usd']
    artifact = tmp_path / 'calls/call-001.json'
    record = json.loads(artifact.read_text(encoding='utf-8'))
    assert record['status'] == 'failed'
    assert record['error_type'] == 'TimeoutError'
    assert record['duration_seconds'] == pytest.approx(1.25)
    assert 'credential-bearing arbitrary message' not in artifact.read_text(encoding='utf-8')
    assert 'nonsecret-test-credential' not in artifact.read_text(encoding='utf-8')


def test_real_worker_timeout_stops_pilot_and_preserves_accounting(tmp_path, monkeypatch):
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from benchmark.nara_http_transport import _loopback_transport

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            requests.append(self.rfile.read(int(self.headers['Content-Length'])))
            time.sleep(5)
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{}')
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    pricing = {provider.MODEL: {'input': 0.1, 'output': 0.2}}
    monkeypatch.setitem(router_module.COST_RATES, provider.MODEL, pricing[provider.MODEL])
    guard = SpendGuard(tmp_path / 'accounting.json', pricing=pricing)
    router = HybridLLMRouter(cloud_model=provider.MODEL, routing_strategy='cloud-only',
                            remote_model_ids=[provider.MODEL], spend_guard=guard)

    def transport(url, headers, body, timeout):
        assert url == provider.ENDPOINT
        return _loopback_transport('http://127.0.0.1:' + str(server.server_port),
                                   headers, body, 3)

    try:
        pilot = provider.NaraPilot(api_key='nonsecret-fixture-key', router=router,
                                   output_dir=tmp_path / 'calls', transport=transport)
        with pytest.raises(ValueError, match='TransportDeadlineExceeded'):
            pilot.factory('system', 'processing_agent').query('public input')
        with pytest.raises(provider.StudyStop):
            pilot.factory('system', 'reasoning_agent').query('no second request')
        record = json.loads((tmp_path / 'calls/call-001.json').read_text(encoding='utf-8'))
        assert record['transport_deadline_exceeded'] is True
        assert record['duration_seconds'] >= 3
        assert len(requests) == pilot.calls == 1
        events = guard.report()['events']
        assert [event['event'] for event in events] == ['reserve', 'settle']
        assert events[1]['failed'] is True
        assert events[1]['usage_source'] == 'reservation'
        assert events[1]['amount_usd'] == events[0]['amount_usd']
        assert guard.report()['reserved_usd'] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
