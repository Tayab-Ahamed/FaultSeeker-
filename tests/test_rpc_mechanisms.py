import json
import pytest
from faultseeker.utils import rpc_provider as rpc


def test_rpc_latency_ema_really_uses_point_two():
    metric = rpc._Metrics()
    metric.record(100,True)
    assert metric.ema_ms == pytest.approx(.2*100+.8*500)
    metric.record(900,False)
    assert metric.ema_ms == pytest.approx(.2*900+.8*420)


def test_cache_enforces_lru_and_ttl(monkeypatch):
    now = [100.]
    monkeypatch.setattr(rpc.time,'time',lambda:now[0])
    cache = rpc._LRUCache(max_size=2,ttl_secs=600)
    cache.set('a',1); cache.set('b',2)
    assert cache.get('a') == (True,1)
    cache.set('c',3)
    assert cache.get('b')[0] is False
    now[0] += 601
    assert cache.get('a')[0] is False
    assert rpc._cache._max == 512
    assert rpc._cache._ttl == 600


def test_circuit_breaker_opens_and_requires_three_clean_recovery_probes(monkeypatch):
    now = [100.]
    monkeypatch.setattr(rpc.time,'time',lambda:now[0])
    provider = rpc._RPCProvider('https://fixture.invalid')
    for _ in range(4):
        provider.penalize(100,10)
    assert provider.is_circuit_open
    now[0] += 61
    assert provider._is_half_open
    provider.reward(100); provider.reward(100)
    assert provider._is_half_open
    provider.reward(100)
    assert not provider._is_half_open
    assert provider._cb_until == 0


def test_batch_preserves_request_order_and_falls_back_after_batch_failure(monkeypatch):
    provider = rpc._RPCProvider('https://fixture.invalid')
    monkeypatch.setattr(rpc._registry,'sorted_providers',lambda chain:[provider])
    def out_of_order(url,payload,timeout):
        requests = json.loads(payload)
        return [{'id':item['id'],'result':item['params'][0]} for item in reversed(requests)]
    monkeypatch.setattr(rpc,'_http_post',out_of_order)
    calls = [('fixture_echo',[1]),('fixture_echo',[2])]
    assert rpc.rpc_batch('eth',calls,cacheable=False) == [1,2]
    monkeypatch.setattr(rpc,'_http_post',lambda *a,**k: {'invalid':'batch response'})
    monkeypatch.setattr(rpc,'rpc_call',lambda chain,method,params,**kwargs: params[0]+10)
    assert rpc.rpc_batch('eth',calls,cacheable=False) == [11,12]


def test_missing_batch_response_is_not_silently_accepted_as_null(monkeypatch):
    provider = rpc._RPCProvider('https://fixture.invalid')
    monkeypatch.setattr(rpc._registry,'sorted_providers',lambda chain:[provider])
    monkeypatch.setattr(rpc,'_http_post',lambda *a,**k:[{'id':0,'result':'first'}])
    monkeypatch.setattr(rpc,'rpc_call',lambda chain,method,params,**kwargs:params[0])
    assert rpc.rpc_batch('eth',[('echo',[1]),('echo',[2])],cacheable=False) == [1,2]
