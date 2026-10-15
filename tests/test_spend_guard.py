"""A durable spend cap blocks an over-budget cloud dispatch before it happens."""

import pytest
from concurrent.futures import ThreadPoolExecutor

from faultseeker.core.spend_guard import BudgetApprovalRequired, SpendGuard


def test_reservation_survives_restart_and_blocks_cumulative_overspend(tmp_path):
    ledger = tmp_path / "spend.json"
    pricing = {"cloud": {"input": 1_000_000, "output": 0}}
    first = SpendGuard(ledger_path=ledger, limit_usd=10, pricing=pricing)
    reservation = first.reserve("cloud", 6, 0)
    first.settle(reservation, 6, 0)

    restarted = SpendGuard(ledger_path=ledger, limit_usd=10, pricing=pricing)
    with pytest.raises(BudgetApprovalRequired):
        restarted.reserve("cloud", 5, 0)
    assert restarted.report()["spent_usd"] == 6


@pytest.mark.parametrize("amount", [-1, float('nan'), float('inf')])
def test_invalid_budget_values_fail_closed(tmp_path, amount):
    with pytest.raises(ValueError):
        SpendGuard(tmp_path / 'spend.json', limit_usd=amount)


def test_unknown_cloud_price_cannot_be_treated_as_free(tmp_path):
    guard = SpendGuard(tmp_path / 'spend.json', pricing={})
    with pytest.raises(ValueError, match='Unknown cloud pricing'):
        guard.reserve('unpriced-model', 100, 100)
    assert not (tmp_path / 'spend.json').exists()


def test_failed_call_without_usage_keeps_full_reservation(tmp_path):
    pricing = {'cloud': {'input': 1_000_000, 'output': 0}}
    guard = SpendGuard(tmp_path / 'spend.json', pricing=pricing)
    reservation = guard.reserve('cloud', 3, 0)
    assert guard.settle(reservation, failed=True) == 3
    report = guard.report()
    assert report['spent_usd'] == 3
    assert report['events'][-1]['usage_source'] == 'reservation'


def test_concurrent_reservations_cannot_spend_same_remaining_budget(tmp_path):
    ledger = tmp_path / 'spend.json'
    pricing = {'cloud': {'input': 1_000_000, 'output': 0}}

    def reserve_once():
        try:
            return SpendGuard(ledger, limit_usd=10, pricing=pricing).reserve('cloud', 6, 0)
        except BudgetApprovalRequired:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        reservations = list(pool.map(lambda _: reserve_once(), range(2)))
    assert sum(reservation is not None for reservation in reservations) == 1
    assert SpendGuard(ledger, limit_usd=10, pricing=pricing).report()['reserved_usd'] == 6


def test_direct_cloud_agent_cannot_bypass_cumulative_budget(monkeypatch,tmp_path):
    from faultseeker.utils.agent import GPTAgent
    from faultseeker.core.llm_router import COST_RATES
    monkeypatch.setenv('OPENAI_API_KEY','local-budget-fixture')
    agent = GPTAgent('system','gpt-4o-mini')
    agent.spend_guard = SpendGuard(tmp_path/'ledger.json',limit_usd=0,pricing=COST_RATES)
    dispatched = []
    monkeypatch.setattr(agent,'_send_message',lambda *a:dispatched.append(True) or '{}')
    with pytest.raises(BudgetApprovalRequired):
        agent.query('inspect')
    assert dispatched == []


def test_windows_lock_contention_retries_nonblocking_and_yields_to_owner(monkeypatch):
    from faultseeker.core import spend_guard
    from types import SimpleNamespace
    calls=[]; sleeps=[]
    class Handle:
        def fileno(self): return 9
        def seek(self,offset): assert offset==0
    def locking(fd,mode,length):
        calls.append((fd,mode,length))
        if len(calls)==1:raise OSError(36,'Resource deadlock avoided')
    api=SimpleNamespace(LK_NBLCK=2,locking=locking)
    monkeypatch.setattr(spend_guard.time,'sleep',sleeps.append)
    SpendGuard._acquire_windows_lock(Handle(),api)
    assert calls==[(9,2,1),(9,2,1)]
    assert sleeps and 0<sleeps[0]<1


def test_windows_lock_unexpected_failure_is_not_retried(monkeypatch):
    from types import SimpleNamespace
    class Handle:
        def fileno(self):return 9
        def seek(self,offset):pass
    def locking(*args):raise OSError(5,'I/O failure')
    with pytest.raises(OSError,match='I/O failure'):
        SpendGuard._acquire_windows_lock(Handle(),SimpleNamespace(LK_NBLCK=2,locking=locking))
