import json
from contextlib import contextmanager
from pathlib import Path
from benchmark.research_protocol import write_json


def test_frozen_opcode_acquisition_preserves_prefreeze_index_and_uses_train_only(tmp_path, monkeypatch):
    from scripts import capture_authentic_opcodes as runner
    base = tmp_path / "reports/cohort_rebuild_v2"
    write_json(base / "opcode_acquisition.json", {"preserve": "prefreeze historical evidence"})
    write_json(tmp_path / "benchmark/eval_split.json", {"status": "FROZEN"})
    row = {"chain": "eth", "txn_hash": "0x" + "a" * 64}
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BASE", base)
    monkeypatch.setattr(runner, "dotenv_values", lambda _: {"DRPC_RPC_URL": "https://example.invalid"})
    previous_row = {"chain": "eth", "txn_hash": "0x" + "b" * 64}
    previous = {"identity": "eth:" + previous_row["txn_hash"], "status": "UNAVAILABLE", "reason": "previous attempt"}
    write_json(base / "opcode_acquisition_train.json", {"attempts": [previous]})
    monkeypatch.setattr(runner, "acquisition_records", lambda *_: [row, previous_row])
    monkeypatch.setattr(runner, "admit", lambda *_: {"accepted": True})
    class Meter:
        count = 0
        max_requests = 1
        def __init__(self, *args, **kwargs): pass
        def summary(self): return {"outbound_rpc_requests": 0}
    @contextmanager
    def proxy(_):
        yield "http://localhost:1"
    def replay(*args, **kwargs):
        raise RuntimeError("deliberate unit-test replay failure")
    monkeypatch.setattr(runner, "MeteredRPC", Meter)
    monkeypatch.setattr(runner, "upstream_proxy", proxy)
    monkeypatch.setattr(runner, "replay_one", replay)
    runner.run([row["txn_hash"]])
    assert json.loads((base / "opcode_acquisition.json").read_text()) == {"preserve": "prefreeze historical evidence"}
    observed = json.loads((base / "opcode_acquisition_train.json").read_text())
    assert previous in observed["attempts"]
    assert observed["attempts"][0]["identity"] == "eth:" + row["txn_hash"]
    assert observed["attempts"][0]["reason"] == "deliberate unit-test replay failure"


def test_proxy_failure_diagnostic_records_method_but_never_params_or_exception_secret():
    from scripts.replay_historical_opcodes import proxy_failure_diagnostic
    secret = "SECRET_CREDENTIAL_VALUE"
    failure = proxy_failure_diagnostic(
        {"method": "eth_getBlockByNumber", "params": [secret]},
        RuntimeError("https://upstream.invalid/" + secret))
    assert failure["methods"] == ["eth_getBlockByNumber"]
    assert failure["error_type"] == "RuntimeError"
    assert secret not in json.dumps(failure)
    assert "params" not in failure
    assert proxy_failure_diagnostic({"method": secret}, ValueError())["methods"] == ["INVALID_METHOD"]


def test_anvil_optional_account_reads_are_allowlisted_without_allowing_writes():
    from scripts.replay_historical_opcodes import READ_METHODS
    assert {"eth_gasPrice", "eth_getAccountInfo"} <= READ_METHODS
    assert "eth_sendRawTransaction" not in READ_METHODS


def test_real_train_captures_pass_canonical_revalidation_and_have_storage_events():
    from scripts.replay_historical_opcodes import validate_recorded_capture
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    expected = {
        "0x9a97d85642f956ad7a6b852cf7bed6f9669e2c2815f3279855acf7f1328e7d46": (668, 220),
        "0xc310a0affe2169d1f6feec1c63dbc7f7c62a887fa48795d327d4d2da2d6b111d": (448, 95),
    }
    for tx, counts in expected.items():
        path = root / "reports/cohort_rebuild_v2/opcodes" / (tx + ".json.gz")
        proof = validate_recorded_capture(path, tx)
        assert (proof["sload_count"], proof["sstore_count"]) == counts
        assert proof["storage_owners_verified"]
    import gzip
    euler = json.loads(gzip.decompress((root / "reports/cohort_rebuild_v2/opcodes" / (list(expected)[1] + ".json.gz")).read_bytes()))
    assert euler["fork_read_cache"]["cache_hits"] > 0
