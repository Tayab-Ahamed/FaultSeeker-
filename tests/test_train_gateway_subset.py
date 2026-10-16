"""Software-only TRAIN subset tests; no model outcomes or research evidence."""
import sys
sys.modules['readline'] = None
import pytest
from scripts import run_train_gateway_pilot as runner

A = 'eth:0x' + 'a' * 64
B = 'eth:0x' + 'b' * 64


@pytest.mark.parametrize('requested', [[], [A, A], ['eth:0x' + 'f' * 64], 'not-a-list'])
def test_invalid_subset_rejected_before_ledger_or_credentials(tmp_path, monkeypatch, requested):
    monkeypatch.setattr(runner, 'configuration', lambda root: ({'train_identities': [A, B]}, {}))
    monkeypatch.setattr(runner, 'SpendGuard', lambda *a, **k: pytest.fail('Ledger instantiated'))
    with pytest.raises(ValueError, match='subset'):
        runner.run(tmp_path, live=True, requested_ids=requested)
    assert not list(tmp_path.rglob('*'))


def test_selector_preserves_default_and_requested_order_without_mutation():
    protocol = {'train_identities': [A, B]}
    assert runner.select_train_identities(protocol) == [A, B]
    assert runner.select_train_identities(protocol, [B]) == [B]
    assert runner.select_train_identities(protocol, [B, A]) == [B, A]
    assert protocol == {'train_identities': [A, B]}


def test_cli_propagates_repeatable_identity_subset(monkeypatch):
    calls = []
    monkeypatch.setattr(runner, 'run', lambda **kw: calls.append(kw))
    runner.main(['--live', '--identity', B, '--identity', A])
    assert calls == [{'live': True, 'approval_file': None, 'requested_ids': [B, A]}]


def test_selected_subset_controls_execution_and_persisted_request_counts(tmp_path, monkeypatch):
    import json
    from contextlib import nullcontext
    from pathlib import Path
    from types import SimpleNamespace
    from benchmark.research_protocol import bind, write_json
    base=tmp_path/runner.BASE
    protocol={'train_identities':[A,B], 'seed':1729,'experiment':'software-test', 'source_inputs':{}}
    write_json(base/'provider_pilot/protocol.json',protocol)
    approval=base/'provider_pilot/approval.json'
    write_json(approval,{})
    write_json(tmp_path/'benchmark/eval_split.json',{'status':'FROZEN','train_ids':[A,B]})
    monkeypatch.setattr(runner,'configuration',lambda root:(protocol,{'input':1,'output':1}))
    monkeypatch.setattr(runner,'approved_call_cap',lambda *a:20)
    monkeypatch.setattr(runner,'approved_budget_limit',lambda *a:10)
    class Guard:
        def __init__(self,*a,**kw): pass
        def report(self): return {'spent_usd':0}
    monkeypatch.setattr(runner,'SpendGuard',Guard)
    monkeypatch.setattr(runner,'system_identity',lambda *a:{})
    def snapshot(system,out):
        path=out/'snapshot.json';write_json(path,{});return path
    monkeypatch.setattr(runner,'snapshot_system',snapshot)
    monkeypatch.setattr(runner,'HybridLLMRouter',lambda **kw:SimpleNamespace())
    monkeypatch.setattr('dotenv.dotenv_values',lambda path:{'BYNARA_API_KEY':'software-fixture'})
    actual_exists=Path.exists
    monkeypatch.setattr(Path,'exists',lambda path:True if path.name=='.env' else actual_exists(path))
    class Pilot:
        calls=0
        stop_reason=''
        factory=None
        stop_after_analysis_error=None
        def __init__(self,**kw):pass
    monkeypatch.setattr(runner,'NaraPilot',Pilot)
    loaded=[]
    def inputs(root,key,require_opcodes=True):
        loaded.append(key)
        result=SimpleNamespace(repeated_patterns=[],function_call_loc_memo={})
        return SimpleNamespace(structured={'transaction_hash':key.split(':')[1]},evidence={},orchestrator=lambda out:SimpleNamespace(run=lambda *a:(result,{},{})))
    monkeypatch.setattr(runner,'load_train_inputs',inputs)
    monkeypatch.setattr(runner,'no_network',lambda:nullcontext())
    monkeypatch.setattr(runner,'FunctionRanker',lambda:SimpleNamespace(rank=lambda *a:None))
    monkeypatch.setattr(runner.VerifiedSourceDownloader,'factory',lambda **kw:None)
    # Deliberate incomplete SOFTWARE observation: never claim measured success.
    monkeypatch.setattr(runner,'FunctionAnalyzer',lambda **kw:SimpleNamespace(run=lambda *a:{'analysis_complete':False}))
    monkeypatch.setattr(runner,'append_experiment',lambda *a:None)
    report=runner.run(tmp_path,live=True,requested_ids=[B])
    assert loaded==[B]
    assert report['requested_train_identities']==[B]
    assert report['requested_train_cases']==1
    assert report['config']['requested_train_identities']==[B]
    assert report['config']['requested_train_cases']==1
    assert report['complete_cases']==0 and report['metrics'] is None
