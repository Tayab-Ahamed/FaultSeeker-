"""Sanitized metered RPC HTTP failure diagnostics; no live network calls."""
import io
import json
from urllib.error import HTTPError
import pytest
from scripts import replay_historical_opcodes as runner


@pytest.mark.parametrize('status',[403,429,503])
def test_http_failure_retains_only_status_and_settles_exactly_once(tmp_path,monkeypatch,status):
    secret='DO_NOT_PERSIST_SENTINEL'
    calls=[]
    def fail(request,timeout):
        calls.append(request)
        raise HTTPError('https://example.invalid/'+secret,status,secret,{'Authorization':secret},io.BytesIO(secret.encode()))
    monkeypatch.setattr(runner,'urlopen',fail)
    meter=runner.MeteredRPC('https://example.invalid/'+secret,tmp_path/'ledger.json',max_requests=4)
    with pytest.raises(RuntimeError) as caught:
        meter.forward({'jsonrpc':'2.0','id':1,'method':'eth_chainId','params':[]})
    error=caught.value
    assert isinstance(error,runner.UpstreamHTTPError)
    assert error.http_status==status and type(error.http_status) is int
    assert str(error)=='Upstream HTTP '+str(status)
    assert secret not in str(error) and secret not in repr(error)
    assert not hasattr(error,'url') and not hasattr(error,'headers') and not hasattr(error,'body')
    report=meter.guard.report()
    assert len(calls)==meter.count==1
    assert [e['event'] for e in report['events']]==['reserve','settle']
    assert report['events'][-1]['failed'] is True
    assert report['reserved_usd']==0
    assert report['spent_usd']==pytest.approx(.000006)
    assert secret not in json.dumps(report)


@pytest.mark.parametrize('status',[True,'403',None,99,600,-1])
def test_http_error_class_rejects_unvalidated_status(status):
    with pytest.raises(ValueError):runner.UpstreamHTTPError(status)
