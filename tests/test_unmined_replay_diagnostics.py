"""Unaccepted replay attempts retain actual pool and nonce evidence."""
import json
from benchmark.research_protocol import read_bound


def test_unmined_diagnostic_preserves_actual_missing_prefix_pool_and_nonce(tmp_path, monkeypatch):
    from scripts import replay_historical_opcodes as runner
    sender = "0x" + "11" * 20
    first = {"hash": "0x" + "a" * 64, "from": sender, "nonce": "0x1", "gas": "0x5208"}
    target = {"hash": "0x" + "b" * 64, "from": sender, "nonce": "0x2", "gas": "0x100000", "gasPrice": "0x5"}
    canonical = {"number": "0x10", "gasLimit": "0x989680", "baseFeePerGas": "0x4"}
    actual = {"number": "0x10", "transactions": [first["hash"]], "gasUsed": "0x5208", "gasLimit": "0x989680"}
    def rpc(url, method, params):
        if method == "eth_getBlockByNumber": return actual
        if method == "txpool_content": return {"pending": {sender: {"2": target}}, "queued": {}}
        if method == "eth_getTransactionCount": return "0x2"
        raise AssertionError(method)
    monkeypatch.setattr(runner, "local_rpc", rpc)
    evidence = runner.save_unmined_diagnostic("http://127.0.0.1:1", canonical, [first, target], target, tmp_path / "out", tmp_path)
    data = json.loads(read_bound(evidence, tmp_path))
    assert data["expected_prefix_hashes"] == [first["hash"], target["hash"]]
    assert data["observed_block"]["transactions"] == [first["hash"]]
    assert data["pool"]["pending"][0]["hash"] == target["hash"]
    assert data["sender_nonce"]["latest"] == "0x2"
    assert data["accepted_capture"] is False
    assert "input" not in data["pool"]["pending"][0]
