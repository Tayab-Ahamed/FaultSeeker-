"""PoW mixHash is preserved too; equality checks must not be relaxed."""

def test_london_environment_setup_sets_canonical_mixhash(monkeypatch):
    from scripts import replay_historical_opcodes as runner
    observed = []
    monkeypatch.setattr(runner, "local_rpc", lambda url, method, params: observed.append((method, params)))
    block = {"timestamp": hex(1648342900), "number": hex(14465357),
             "baseFeePerGas": "0x10", "miner": "0x" + "11" * 20, "mixHash": "0x" + "22" * 32}
    runner.configure_block_environment("http://127.0.0.1:1", block)
    assert ("anvil_setNextBlockPrevRandao", [block["mixHash"]]) in observed
    assert ("anvil_setNextBlockBaseFeePerGas", [block["baseFeePerGas"]]) in observed
