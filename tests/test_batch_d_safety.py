"""Software safety tests only; these fixtures are not research evidence."""
import json
from pathlib import Path

import pytest

from scripts.research import batchD_phase2 as runner


@pytest.mark.parametrize("status,body", [
    (402, {"error": {"message": "Payment required"}}),
    (200, {"error": {"message": "Upgrade to a paid plan"}}),
    (429, {"error": {"message": "rate limit"}}),
])
def test_dispatch_stops_on_billing_or_rate_limit(status, body, monkeypatch, tmp_path):
    monkeypatch.setattr(runner.base, "_rpc_once", lambda *args: ({"http_status": status, "body": body}, ""))
    state = {"request_count": 0, "run_dir": tmp_path, "api_key": "private", "rate_limit_hits": 0,
             "billing_prompt_detected": False}
    with pytest.raises(RuntimeError):
        runner.safe_rpc("https://example.invalid/private", "eth_chainId", [], state)
    assert state["request_count"] == 1
    assert "private" not in (tmp_path / "requests.jsonl").read_text()


def test_source_file_mutation_rejects_frozen_code(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    code = tmp_path / "ranker.py"
    code.write_text("original")
    manifest = {"ranker.py": runner.sha256(code)}
    runner.verify_code(manifest)
    code.write_text("changed")
    with pytest.raises(RuntimeError, match="ranker.py"):
        runner.verify_code(manifest)


def test_score_lock_is_exclusive(tmp_path):
    runner.acquire_score_lock(tmp_path)
    with pytest.raises(FileExistsError):
        runner.acquire_score_lock(tmp_path)


def test_label_fields_never_enter_candidate_inputs():
    result = runner.trace_text({"to": "0x" + "11" * 20, "input": "0x12345678" + "00" * 32,
                                "type": "CALL", "vulnerable_contract_address": "LABEL_ONLY"})
    assert "0x12345678" in result
    assert "LABEL_ONLY" not in result


def test_evidence_redaction_never_truncates_public_calldata():
    value = {"input": "0x" + "ab" * 20000, "diagnostic": "https://rpc.invalid/key"}
    result = runner.redact_exact(value, "https://rpc.invalid/key", "key")
    assert result["input"] == value["input"]
    assert result["diagnostic"] == "[RPC_URL_REDACTED]"


def test_invalid_json_response_still_logs_attempt(monkeypatch, tmp_path):
    def fail(*args):
        raise ValueError("private response")
    monkeypatch.setattr(runner.base, "_rpc_once", fail)
    state = {"request_count": 0, "run_dir": tmp_path, "api_key": "private", "rate_limit_hits": 0,
             "billing_prompt_detected": False}
    with pytest.raises(RuntimeError):
        runner.safe_rpc("https://example.invalid/private", "eth_chainId", [], state)
    log = (tmp_path / "requests.jsonl").read_text()
    assert "private" not in log
    assert json.loads(log)["transport_error"] == "ValueError"
