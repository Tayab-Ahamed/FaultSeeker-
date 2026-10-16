"""Standing TRAIN authorization changes caps, never inputs or cumulative spend."""
import sys
sys.modules['readline'] = None
import pytest
from scripts.run_train_gateway_pilot import approved_call_cap, approved_budget_limit
from benchmark.nara_pilot_provider import NaraPilot, MODEL, ENDPOINT
from faultseeker.core.llm_router import HybridLLMRouter


def approval():
    return {'approved': True, 'mode': 'standing-train-daily-allowance',
            'max_completion_requests': None, 'daily_token_limit': 7_000_000,
            'model': MODEL, 'destination': ENDPOINT, 'protocol': {'path': 'p', 'sha256': 'h'},
            'stop_on_any_error': True, 'train_only': True, 'labels_excluded': True,
            'heldout_excluded': True, 'paper_env_excluded': True}


def test_standing_approval_removes_request_cap_but_retains_cumulative_spend_cap():
    a = approval()
    assert approved_call_cap(a, a['protocol']) is None
    assert approved_budget_limit(a, {'spent_usd': 1.9262008}) == 10


@pytest.mark.parametrize('change', [
    {'daily_token_limit': 7_000_001}, {'daily_token_limit': True},
    {'model': 'other'}, {'train_only': False}, {'labels_excluded': False},
    {'heldout_excluded': False}, {'paper_env_excluded': False},
    {'stop_on_any_error': False}, {'destination': 'https://other.example'},
    {'max_completion_requests': 20}, {'max_incremental_estimated_usd': .2},
])
def test_standing_approval_rejects_changed_or_ambiguous_scope(change):
    a = dict(approval(), **change)
    with pytest.raises(ValueError):
        approved_call_cap(a, a['protocol'])


def test_uncapped_pilot_requires_daily_guard_before_any_dispatch(tmp_path):
    class Guard:
        pass
    router = HybridLLMRouter(cloud_model=MODEL, routing_strategy='cloud-only',
                            remote_model_ids=[MODEL], spend_guard=Guard())
    with pytest.raises(ValueError, match='daily'):
        NaraPilot(api_key='fixture', router=router, output_dir=tmp_path, max_calls=None)


def test_uncapped_pilot_passes_twenty_and_stops_on_first_error(tmp_path, monkeypatch):
    import json
    from benchmark.pilot_token_guard import DailyTokenGuard
    from benchmark.nara_pilot_provider import StudyStop
    from faultseeker.core.spend_guard import SpendGuard
    import faultseeker.core.llm_router as module
    rates = {'input': .1, 'output': .2}
    monkeypatch.setitem(module.COST_RATES, MODEL, rates)
    guard = SpendGuard(tmp_path/'spend.json', pricing={MODEL: rates})
    tokens = DailyTokenGuard(tmp_path/'tokens.json')
    router = HybridLLMRouter(cloud_model=MODEL, routing_strategy='cloud-only',
                            remote_model_ids=[MODEL], spend_guard=guard)
    calls=[]
    def transport(url, headers, body, timeout):
        calls.append(body)
        if len(calls)==22:return 429,b'{}',url
        return 200,json.dumps({'model':MODEL,'choices':[{'message':{'content':'{"ok":true}'},'finish_reason':'stop'}],
                               'usage':{'prompt_tokens':10,'completion_tokens':5}}).encode(),url
    pilot=NaraPilot(api_key='fixture-key',router=router,output_dir=tmp_path/'calls',
                    max_calls=None,daily_token_guard=tokens,transport=transport,sleep=lambda n:None)
    agent=pilot.factory('system','processing_agent')
    for _ in range(21):assert agent.query('public fixture')['ok']
    with pytest.raises(ValueError):agent.query('first error')
    with pytest.raises(StudyStop):agent.query('no retry')
    assert len(calls)==22
    assert len(guard.report()['events'])==44
    assert tokens.report()['reserved']==0
    assert len(tokens.report()['events'])==44


def test_daily_guard_refuses_before_transport(tmp_path,monkeypatch):
    from benchmark.pilot_token_guard import DailyTokenGuard,DailyTokenLimitReached
    from faultseeker.core.spend_guard import SpendGuard
    import faultseeker.core.llm_router as module
    rates={'input':.1,'output':.2};monkeypatch.setitem(module.COST_RATES,MODEL,rates)
    guard=SpendGuard(tmp_path/'spend.json',pricing={MODEL:rates})
    router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',remote_model_ids=[MODEL],spend_guard=guard)
    tokens=DailyTokenGuard(tmp_path/'tokens.json',limit_tokens=1)
    def forbidden(*args):raise AssertionError('Must not dispatch')
    pilot=NaraPilot(api_key='fixture-key',router=router,output_dir=tmp_path/'calls',max_calls=None,daily_token_guard=tokens,transport=forbidden)
    with pytest.raises(DailyTokenLimitReached):pilot.factory('system').query('input')
    assert pilot.calls==0 and not list((tmp_path/'calls').glob('call-*.json'))
    assert guard.report()['spent_usd']==0
    assert guard.report()['reserved_usd']==0


def test_real_historical_usage_is_imported_once_without_provider_dispatch(tmp_path):
    from pathlib import Path
    from benchmark.pilot_token_guard import DailyTokenGuard
    from scripts.run_train_gateway_pilot import import_historical_tokens
    root=Path(__file__).resolve().parents[1]
    existing=root/'data/research/nara_daily_tokens.json'
    if existing.exists():
        # Real standing calls already have settlements. Copy their accounting
        # into an isolated test ledger; never reset or mutate the real ledger.
        (tmp_path/'tokens.json').write_bytes(existing.read_bytes())
    guard=DailyTokenGuard(tmp_path/'tokens.json')
    import_historical_tokens(guard,root)
    first=guard.report()
    import_historical_tokens(guard,root)
    second=guard.report()
    assert first['used']==second['used']
    assert first['events']==second['events']
    assert len(first['imports'])>=30
    assert all(i['tokens']>0 for i in first['imports'].values())


def test_standing_token_settlements_are_not_imported_again(tmp_path):
    import json
    from benchmark.pilot_token_guard import DailyTokenGuard
    from benchmark.research_protocol import bind
    from scripts.run_train_gateway_pilot import import_historical_tokens
    root=tmp_path;out=root/'reports/cohort_rebuild_v2/gateway_runs/20261016T010000-12345678'
    out.mkdir(parents=True)
    guard=DailyTokenGuard(root/'tokens.json')
    reservation=guard.reserve(100,10);guard.settle(reservation,5,2)
    record={'requested_alias':MODEL,'daily_token_accounting':{'reservation_id':reservation,'charged_tokens':7}}
    path=out/'call.json';path.write_text(json.dumps(record))
    (out/'summary.json').write_text(json.dumps({'run_id':out.name,'calls':[bind(path,root)]}))
    import_historical_tokens(guard,root)
    assert guard.report()['used']==7 and not guard.report()['imports']
    # A missing daily ledger is an accounting error, never silently reset free.
    guard2=DailyTokenGuard(root/'missing-tokens.json')
    with pytest.raises(ValueError,match='settlement'):
        import_historical_tokens(guard2,root)
