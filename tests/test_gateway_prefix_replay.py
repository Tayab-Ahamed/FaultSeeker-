"""Strict, real-observation HTTP tape tests; never a new quality experiment."""
import json
from pathlib import Path
import pytest
from benchmark.research_protocol import bind,sha,write_json
from benchmark.nara_pilot_provider import ENDPOINT,MODEL
from scripts import replay_train_gateway_prefix as replay
ROOT=Path(__file__).resolve().parents[1]


def record(tmp_path):
    request={'model':MODEL,'messages':[{'role':'user','content':'actual request'}]}
    body=json.dumps(request,ensure_ascii=False).encode()
    response={'model':MODEL,'choices':[{'message':{'content':'[]'}}]}
    raw=json.dumps(response).encode()
    item={'call_number':1,'endpoint':ENDPOINT,'requested_alias':MODEL,'request':request,'request_sha256':sha(body),
        'request_bytes':len(body),'response_text':raw.decode(),'response_sha256':sha(raw),'response_bytes':len(raw),
        'http_status':200,'response':response,'returned_alias':MODEL}
    path=tmp_path/'call.json';write_json(path,item)
    return item,path,body


def test_strict_tape_returns_only_exact_bound_observation_then_stops(tmp_path):
    item,path,body=record(tmp_path);tape=replay.StrictTape([bind(path,tmp_path)],tmp_path)
    status,raw,url=tape(ENDPOINT,{},body,60)
    assert raw==item['response_text'].encode() and status==200 and url==ENDPOINT
    assert tape.matched==1
    with pytest.raises(replay.ReplayBoundary,match='EXHAUSTED'):tape(ENDPOINT,{},body,60)


@pytest.mark.parametrize('mutation',['request_bytes','json','endpoint','model','response_sha','response_json'])
def test_changed_requests_or_corrupt_responses_stop_before_return(tmp_path,mutation):
    item,path,body=record(tmp_path);url=ENDPOINT
    if mutation=='request_bytes':body=json.dumps(item['request'],separators=(',',':')).encode()
    if mutation=='json':
        payload=dict(item['request'],temperature=1);body=json.dumps(payload).encode()
    if mutation=='endpoint':url='https://wrong.invalid'
    if mutation=='model':item['request']['model']='other';write_json(path,item)
    if mutation=='response_sha':item['response_sha256']='0'*64;write_json(path,item)
    if mutation=='response_json':item['response']={'model':'other'};write_json(path,item)
    tape=replay.StrictTape([bind(path,tmp_path)],tmp_path)
    with pytest.raises(replay.ReplayBoundary):tape(url,{},body,60)
    assert tape.matched==0


def test_real_saved_response_prefix_matches_bytes_and_bound_hashes():
    summary=json.loads((ROOT/replay.DEFAULT_SUMMARY).read_text())
    tape=replay.StrictTape(summary['calls'][:2],ROOT)
    for binding in summary['calls'][:2]:
        from benchmark.research_protocol import read_bound
        item=json.loads(read_bound(binding,ROOT))
        saved=item['request']
        # Historical artifact serialization sorted object keys; rebuild the
        # provider's original insertion order, then require its recorded SHA.
        payload={'model':saved['model'],'messages':[{'role':m['role'],'content':m['content']} for m in saved['messages']],
            'temperature':saved['temperature'],'max_tokens':saved['max_tokens'],'stream':saved['stream']}
        body=json.dumps(payload,ensure_ascii=False).encode()
        assert sha(body)==item['request_sha256']
        status,raw,url=tape(ENDPOINT,{},body,60)
        assert sha(raw)==item['response_sha256'] and status==item['http_status']
    assert tape.matched==2


def test_replay_boundary_escapes_broad_production_exception_handlers():
    assert issubclass(replay.ReplayBoundary,BaseException)
    assert not issubclass(replay.ReplayBoundary,Exception)

@pytest.mark.parametrize('mutation',['request_json','response_model','request_length','response_length','record_order','response_text_missing'])
def test_tape_checks_semantics_lengths_alias_and_order_independently(tmp_path,mutation):
    item,path,body=record(tmp_path)
    if mutation=='request_json':
        item['request']=dict(item['request'],temperature=1)
    if mutation=='response_model':
        value=dict(item['response'],model='other')
        raw=json.dumps(value).encode();item.update(response=value,response_text=raw.decode(),response_sha256=sha(raw),response_bytes=len(raw),returned_alias='other')
    if mutation=='request_length':item['request_bytes']+=1
    if mutation=='response_length':item['response_bytes']+=1
    if mutation=='record_order':item['call_number']=2
    if mutation=='response_text_missing':item.pop('response_text')
    write_json(path,item);tape=replay.StrictTape([bind(path,tmp_path)],tmp_path)
    with pytest.raises(replay.ReplayBoundary):tape(ENDPOINT,{},body,60)
    assert tape.matched==0
