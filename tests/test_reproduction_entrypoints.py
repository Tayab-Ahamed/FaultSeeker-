import pytest
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_runner_delegates_arguments_and_propagates_pytest_failure(monkeypatch):
    import run_tests_nopytest
    observed = []
    monkeypatch.setattr(sys, 'argv', ['run_tests_nopytest.py', 'tests', '-q'])
    monkeypatch.setattr(pytest, 'main', lambda arguments: observed.append(arguments) or 1)
    assert run_tests_nopytest.main() == 1
    assert observed == [['tests', '-q']]


def test_original_test_sources_match_the_frozen_baseline_manifest():
    from benchmark.test_integrity import original_test_changes
    assert original_test_changes(ROOT) == []
