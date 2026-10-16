"""Software-only capture/version isolation tests; not empirical paper evidence."""
import gzip
import json
from pathlib import Path

import pytest

from benchmark.research_protocol import bind, identity, write_json
from tests.test_versioned_train_inputs import versioned_workspace, guard_heldout_reads


def setup_runner(root, monkeypatch):
    from scripts import capture_authentic_traces as runner
    original, added, split_path = versioned_workspace(root)
    monkeypatch.setattr(runner, 'ROOT', root)
    monkeypatch.setattr(runner, 'BASE', root / 'reports/cohort_rebuild_v2')
    monkeypatch.setattr(runner, 'dotenv_values', lambda _: {'DRPC_RPC_URL': 'https://lb.drpc.live/ethereum/SECRET'})
    return runner, original, added, split_path


def test_explicit_acquisition_records_select_only_bound_train(tmp_path, monkeypatch):
    from benchmark.research_protocol import acquisition_records
    _, added, split = versioned_workspace(tmp_path)
    guard_heldout_reads(monkeypatch)
    assert acquisition_records(tmp_path, tmp_path / 'NEVER_READ_ADMITTED.json', split_file=split) == [added]


def test_outside_selected_train_rejected_before_meter(tmp_path, monkeypatch):
    runner, original, _, split = setup_runner(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, 'MeteredRPC', lambda *a, **k: pytest.fail('Meter instantiated for excluded identity'))
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='TRAIN'):
        runner.run(split_file=split, requested_ids=[identity(original)])


def test_provider_failure_stops_without_next_dispatch_and_preserves_legacy(tmp_path, monkeypatch):
    runner, _, added, split = setup_runner(tmp_path, monkeypatch)
    legacy = tmp_path / 'reports/cohort_rebuild_v2/trace_acquisition_train.json'
    write_json(legacy, [])
    before = legacy.read_bytes()
    calls = []
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params):
            calls.append(method)
            raise RuntimeError('https://secret.invalid/SECRET')
        def summary(self): return {'outbound_rpc_requests': len(calls), 'estimated_cost_usd': .000006}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    guard_heldout_reads(monkeypatch)
    result = runner.run(split_file=split, requested_ids=[identity(added)])
    assert result['status'] == 'STOPPED_ON_ERROR'
    assert calls == ['eth_chainId']
    assert legacy.read_bytes() == before
    assert result['attempts'][0]['accounting']['outbound_rpc_requests'] == 1
    assert 'SECRET' not in json.dumps(result)


def test_unbound_file_not_reused_as_recorded_capture(tmp_path, monkeypatch):
    runner, _, added, split = setup_runner(tmp_path, monkeypatch)
    raw = tmp_path / 'reports/cohort_rebuild_v2/traces/eth' / (added['txn_hash'] + '.json.gz')
    raw.parent.mkdir(parents=True)
    raw.write_bytes(gzip.compress(b'{}'))
    calls = []
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params):
            calls.append(method)
            raise RuntimeError('Deliberate software failure')
        def summary(self): return {'outbound_rpc_requests': len(calls)}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    result = runner.run(split_file=split, requested_ids=[identity(added)])
    assert calls == ['eth_chainId']
    assert result['attempts'][0]['status'] == 'UNAVAILABLE'
    assert raw.read_bytes() == gzip.compress(b'{}') or gzip.decompress(raw.read_bytes()) == b'{}'


def test_version_capture_is_consumed_and_index_bound_by_both_consumers(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    from scripts import run_authentic_research
    runner, original, _, split = setup_runner(tmp_path, monkeypatch)
    spec = json.loads(split.read_text())
    spec['train_ids'], spec['heldout_ids'] = spec['heldout_ids'], spec['train_ids']
    write_json(split.parent / 'train.json', [original])
    spec['partitions']['train'] = bind(split.parent / 'train.json', tmp_path)
    write_json(split, spec)
    monkeypatch.setattr(runner, 'drpc_url', lambda endpoint, chain: 'https://example.invalid')
    rpc = json.loads((tmp_path / original['rpc']['path']).read_text())
    trace = json.loads(gzip.decompress((tmp_path / original['trace']['path']).read_bytes()))['raw_trace']['call']
    rpc['receipt']['blockNumber'] = rpc['transaction']['blockNumber'] = '0x10'
    write_json(tmp_path / original['rpc']['path'], rpc)
    original['rpc'] = bind(tmp_path / original['rpc']['path'], tmp_path)
    calls = []
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params):
            calls.append(method)
            return hex(rpc['chain_id']) if method == 'eth_chainId' else '0x6000'
        def forward(self, request):
            calls.append(request['method'])
            return {'jsonrpc': '2.0', 'id': 1, 'result': trace}
        def summary(self): return {'outbound_rpc_requests': len(calls)}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    # Remove the row's old trace: consumers must discover the version index.
    del original['trace']
    write_json(split.parent / 'train.json', [original])
    manifest_path = split.parent / 'cohort_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['records'][0] = original
    write_json(manifest_path, manifest)
    spec['manifest'] = bind(manifest_path, tmp_path)
    spec['manifest_sha256'] = spec['manifest']['sha256']
    spec['partitions']['train'] = bind(split.parent / 'train.json', tmp_path)
    write_json(split, spec)
    guard_heldout_reads(monkeypatch)
    result = runner.run(split_file=split, requested_ids=[identity(original)])
    assert result['status'] == 'COMPLETE'
    assert calls[:2] == ['eth_chainId', 'debug_traceTransaction']
    assert all(method == 'eth_getCode' for method in calls[2:])
    inputs = load_train_inputs(tmp_path, identity(original), require_opcodes=False, split_file=split)
    assert inputs.structured['transaction_hash'] == original['txn_hash']
    assert inputs.evidence['acquisition_indexes']
    observed = run_authentic_research.run_train(tmp_path, split_file=split)
    assert observed['config']['acquisition_indexes']
    assert observed['variants']['structural']['coverage']['scored'] == 1
    previous_index_bytes = (tmp_path / result['index']['path']).read_bytes()
    before = list(calls)
    reused = runner.run(split_file=split, requested_ids=[identity(original)])
    assert calls == before
    assert reused['attempts'][0]['status'] == 'RECORDED'
    assert (tmp_path / result['index']['path']).read_bytes() == previous_index_bytes
    snapshot = json.loads((tmp_path / reused['index']['path']).read_text())
    assert len(snapshot['history']) == 2
    assert len(snapshot['attempts']) == 1



def test_calltracer_rpc_error_stops_and_sanitizes_provider_text(tmp_path, monkeypatch):
    runner, _, added, split = setup_runner(tmp_path, monkeypatch)
    calls = []
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params):
            calls.append(method)
            return '0x1'
        def forward(self, request):
            calls.append(request['method'])
            return {'error': {'code': -32000, 'message': 'SECRET upstream credential'}}
        def summary(self): return {'outbound_rpc_requests': len(calls)}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    report = runner.run(split_file=split, requested_ids=[identity(added)])
    assert report['status'] == 'STOPPED_ON_ERROR'
    assert calls == ['eth_chainId', 'debug_traceTransaction']
    assert report['attempts'][0]['rpc_error_code'] == -32000
    assert 'SECRET' not in json.dumps(report)


def test_capture_cli_requires_live_and_propagates_explicit_scope(tmp_path, monkeypatch):
    runner, _, added, split = setup_runner(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(runner, 'run', lambda **kwargs: calls.append(kwargs))
    with pytest.raises(SystemExit):
        runner.main(['--split-file', str(split)])
    assert not calls
    runner.main(['--live', '--split-file', str(split), '--identity', identity(added), '--max-requests', '12'])
    assert calls == [{'split_file': str(split), 'requested_ids': [identity(added)], 'max_requests': 12}]


def test_provider_error_prevents_dispatch_for_remaining_selected_rows(tmp_path, monkeypatch):
    from tests.test_authentic_publication import fixture_record
    runner, _, added, split = setup_runner(tmp_path, monkeypatch)
    extra = fixture_record(tmp_path, 3)
    extra['reentrancy_label'] = False
    spec = json.loads(split.read_text())
    manifest_path = split.parent / 'cohort_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['records'].append(extra)
    manifest['accepted_count'] += 1
    write_json(manifest_path, manifest)
    write_json(split.parent / 'train.json', [added, extra])
    spec['manifest'] = bind(manifest_path, tmp_path)
    spec['manifest_sha256'] = spec['manifest']['sha256']
    spec['train_ids'].append(identity(extra))
    spec['partitions']['train'] = bind(split.parent / 'train.json', tmp_path)
    write_json(split, spec)
    created = []
    class Meter:
        def __init__(self, *args, **kwargs): created.append(self)
        def rpc(self, method, params): raise TimeoutError('PRIVATE endpoint')
        def summary(self): return {'outbound_rpc_requests': 1}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    guard_heldout_reads(monkeypatch)
    report = runner.run(split_file=split)
    assert len(created) == 1
    assert len(report['requested_ids']) == 2 and len(report['attempts']) == 1
    assert report['outbound_rpc_requests'] == 1
    assert report['status'] == 'STOPPED_ON_ERROR'


def test_historical_code_error_stops_before_second_code_request(tmp_path, monkeypatch):
    runner, original, added, split = setup_runner(tmp_path, monkeypatch)
    trace = json.loads(gzip.decompress((tmp_path / original['trace']['path']).read_bytes()))['raw_trace']['call']
    rpc_path = tmp_path / original['rpc']['path']
    rpc = json.loads(rpc_path.read_text())
    rpc['transaction']['blockNumber'] = rpc['receipt']['blockNumber'] = '0x10'
    write_json(rpc_path, rpc)
    original['rpc'] = bind(rpc_path, tmp_path)
    del original['trace']
    spec = json.loads(split.read_text())
    spec['train_ids'], spec['heldout_ids'] = [identity(original)], [identity(added)]
    write_json(split.parent / 'train.json', [original])
    manifest_path = split.parent / 'cohort_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['records'][0] = original
    write_json(manifest_path, manifest)
    spec['manifest'] = bind(manifest_path, tmp_path)
    spec['manifest_sha256'] = spec['manifest']['sha256']
    spec['partitions']['train'] = bind(split.parent / 'train.json', tmp_path)
    write_json(split, spec)
    calls = []
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params):
            calls.append(method)
            if method == 'eth_getCode': raise TimeoutError('SECRET')
            return '0x1'
        def forward(self, request):
            calls.append(request['method'])
            return {'result': trace}
        def summary(self): return {'outbound_rpc_requests': len(calls)}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    report = runner.run(split_file=split)
    assert calls == ['eth_chainId', 'debug_traceTransaction', 'eth_getCode']
    assert report['attempts'][0]['phase'] == 'eth_getCode'
    assert 'artifact' not in report['attempts'][0]
    assert report['status'] == 'STOPPED_ON_ERROR'


def test_meter_rpc_controlled_error_preserves_only_integer_code(tmp_path, monkeypatch):
    runner, _, _, split = setup_runner(tmp_path, monkeypatch)
    class Meter:
        def __init__(self, *args, **kwargs): pass
        def rpc(self, method, params): raise RuntimeError('eth_chainId failed (RPC code -32005)')
        def summary(self): return {'outbound_rpc_requests': 1}
    monkeypatch.setattr(runner, 'MeteredRPC', Meter)
    report = runner.run(split_file=split)
    assert report['attempts'][0]['rpc_error_code'] == -32005
    assert 'RPC code' not in json.dumps(report)
