from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reproduce/measured_cost_run.py"


def _load():
    spec = importlib.util.spec_from_file_location("measured_cost_run", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cost_run_refuses_to_invent_missing_preregistered_selection():
    module = _load()
    report = module.build_blocked_report()
    assert report["requested_runs"]["n100"]["status"] == "BLOCKED_BY_MISSING_PREREGISTERED_CONFIG"
    assert report["requested_runs"]["n100"]["completed_n"] == 0
    assert report["requested_runs"]["extension"]["status"] == "NOT_STARTED"
    assert report["provider_gate"]["dotenv_loaded"] is False
    assert report["provider_gate"]["provider_calls"] == 0
    assert report["measurements"]["per_call_log"] == []
    assert report["resume"]["next_transaction_index"] == 0


def test_cost_run_does_not_treat_unrelated_selection_as_preregistered():
    module = _load()
    assert all(path.name != "new_candidates_initial_selection.json"
               for path in module.candidate_selection_files())
