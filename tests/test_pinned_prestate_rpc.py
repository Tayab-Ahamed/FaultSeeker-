"""Only observed, exact-parent reads can be served from real prestate evidence."""
import gzip
import json
import pytest
from benchmark.research_protocol import bind, write_json


def cache_fixture(root, index=0):
    from scripts.pinned_prestate_rpc import PinnedPrestateRPC
    tx = "0x" + "a" * 64
    blockhash = "0x" + "b" * 64
    address = "0x" + "11" * 20
    prestate = {"transaction_hash": tx, "chain": "eth", "request": {"method": "debug_traceTransaction", "params": [tx,
        {"tracer": "prestateTracer", "tracerConfig": {"diffMode": False, "disableCode": False, "disableStorage": False}}]},
        "response": {"result": {address: {"balance": "0x10", "nonce": 2, "code": "0x6000", "storage": {"0x00": "0x07"}}}}}
    path = root / "prestate.json.gz"
    path.write_bytes(gzip.compress(json.dumps(prestate).encode()))
    receipt = {"transactionHash": tx, "transactionIndex": hex(index), "blockNumber": "0x100", "blockHash": blockhash}
    rpc = root / "rpc.json"
    write_json(rpc, {"receipt": receipt, "transaction": {"hash": tx}, "chain_id": 1})
    row = {"txn_hash": tx, "chain": "eth", "rpc": bind(rpc, root), "prestate": bind(path, root)}
    class Upstream:
        errors = []
        count = 0
        max_requests = 100
        calls = []
        def forward(self, payload):
            self.calls.append(payload)
            self.count += 1
            return {"jsonrpc": "2.0", "id": payload["id"], "result": "upstream"}
        def summary(self): return {"outbound_rpc_requests": self.count}
    upstream = Upstream()
    cache = PinnedPrestateRPC(upstream, row, root)
    block = {"hash": blockhash, "number": "0x100", "timestamp": "0x60000000", "parentHash": "0x" + "d" * 64, "transactions": [{"hash": tx}]}
    return cache, upstream, block, row, address


def request(address, method="eth_getBalance", block="0xff", slot=None):
    params = [address, block] if slot is None else [address, slot, block]
    return {"jsonrpc": "2.0", "id": 123, "method": method, "params": params}


def test_pinned_cache_is_inactive_until_canonical_first_transaction_verified(tmp_path):
    cache, upstream, block, row, address = cache_fixture(tmp_path)
    assert cache.forward(request(address))["result"] == "upstream"
    cache.activate(block, row["txn_hash"])
    assert cache.forward(request(address))["result"] == "0x10"
    assert cache.forward(request(address, "eth_getTransactionCount"))["result"] == "0x2"
    assert cache.forward(request(address, "eth_getCode"))["result"] == "0x6000"
    assert cache.forward(request(address, "eth_getStorageAt", slot="0x0"))["result"] == "0x" + "0" * 63 + "7"
    assert upstream.count == 1


def test_wrong_block_unknown_account_or_missing_slot_always_use_metered_upstream(tmp_path):
    cache, upstream, block, row, address = cache_fixture(tmp_path)
    cache.activate(block, row["txn_hash"])
    assert cache.forward(request(address, block="latest"))["result"] == "upstream"
    assert cache.forward(request(address, block="0xfe"))["result"] == "upstream"
    assert cache.forward(request("0x" + "22" * 20))["result"] == "upstream"
    assert cache.forward(request(address, "eth_getStorageAt", slot="0x1"))["result"] == "upstream"
    assert upstream.count == 4
    assert cache.summary()["prestate_read_cache"]["cache_hits"] == 0


def test_prestate_after_a_block_prefix_cannot_masquerade_as_parent_state(tmp_path):
    with pytest.raises(ValueError, match="first transaction"):
        cache_fixture(tmp_path, index=1)


def test_cache_rejects_changed_canonical_block_and_future_system_transition(tmp_path):
    cache, _, block, row, _ = cache_fixture(tmp_path)
    with pytest.raises(ValueError, match="identity"):
        cache.activate(dict(block, hash="0x" + "c" * 64), row["txn_hash"])
    with pytest.raises(ValueError, match="pre-Shanghai"):
        cache.activate(dict(block, timestamp=hex(1681338455)), row["txn_hash"])


def test_missing_observed_field_is_not_defaulted_to_zero(tmp_path):
    cache, upstream, block, row, address = cache_fixture(tmp_path)
    del cache.accounts[address]["balance"]
    cache.activate(block, row["txn_hash"])
    assert cache.forward(request(address))["result"] == "upstream"
    assert upstream.count == 1


def test_eip1898_exact_parent_hash_is_supported_but_other_hash_is_not(tmp_path):
    cache, upstream, block, row, address = cache_fixture(tmp_path)
    cache.activate(block, row["txn_hash"])
    exact = {"blockHash": block["parentHash"], "requireCanonical": True}
    assert cache.forward(request(address, block=exact))["result"] == "0x10"
    wrong = {"blockHash": "0x" + "e" * 64, "requireCanonical": True}
    assert cache.forward(request(address, block=wrong))["result"] == "upstream"
    assert upstream.count == 1
