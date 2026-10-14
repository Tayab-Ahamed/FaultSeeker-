"""Keep simulated provider usage out of the real cumulative spend ledger."""
import pytest


@pytest.fixture(autouse=True)
def isolate_experiment_spend_ledger(monkeypatch,tmp_path):
    monkeypatch.setenv('FAULTSEEKER_SPEND_LEDGER',str(tmp_path/'fixture-spend-ledger.json'))
