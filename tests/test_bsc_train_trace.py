"""Bounded PublicNode BSC probe tests, transport-only response fixtures."""
import json
from pathlib import Path
import pytest
from scripts import probe_bsc_train_trace as probe


def canonical():
    tx={'hash':probe.TX,'from':'0x'+'11'*20,'to':'0x'+'22'*20,'input':'0x1234','value':'0x0','blockHash':'0x'+'ab'*32,'blockNumber':'0x10','transactionIndex':'0x2'}
    receipt={'transactionHash':probe.TX,'blockHash':tx['blockHash'],'blockNumber':'0x10','transactionIndex':'0x2','status':'0x1','gasUsed':'0x5208','logs':[],'contractAddress':None}
    tree={'from':tx['from'],'to':tx['to'],'input':tx['input'],'value':'0x0','type':'CALL'}
    return {'chain':'bsc','chain_id':56,'txn_hash':probe.TX,'transaction':tx,'receipt':receipt},tree


class RPC:
    def __init__(self,responses):self.responses=list(responses);self.calls=[]
    def forward(self,payload):
        self.calls.append(payload)
        result=self.responses.pop(0)
        if isinstance(result,Exception):raise result
        return result
    def summary(self):return {'outbound_rpc_requests':len(self.calls),'estimated_cost_usd':len(self.calls)*.000006}


def test_probe_refuses_non_live_entry_before_loading_files(tmp_path):
    with pytest.raises(ValueError,match='live'):probe.run_live(root=tmp_path)


def test_debug_capture_requires_live_matching_receipt_and_bound_raw_records(tmp_path):
    rpc,tree=canonical();meter=RPC([{'result':'0x38'},{'result':tree},{'result':rpc['receipt']}])
    summary=probe.probe(meter,rpc,{'path':'known.json','sha256':'a'*64},tmp_path/'probe',tmp_path)
    assert summary['status']=='CAPTURED' and summary['requests']==3
    assert [x['method'] for x in meter.calls]==['eth_chainId','debug_traceTransaction','eth_getTransactionReceipt']
    assert meter.calls[1]['params'][1]=={'tracer':'callTracer','timeout':'15s'}
    from benchmark.research_protocol import read_bound
    capture=json.loads(read_bound(summary['artifact'],tmp_path))
    assert capture['result']==tree
    assert len(summary['raw_requests'])==3


def test_wrong_chain_never_attempts_trace(tmp_path):
    rpc,_=canonical();meter=RPC([{'result':'0x1'}])
    result=probe.probe(meter,rpc,{},tmp_path/'probe',tmp_path)
    assert result['status']=='WRONG_CHAIN' and len(meter.calls)==1


def test_both_trace_failures_preserved_without_receipt_or_retry(tmp_path):
    rpc,_=canonical();meter=RPC([{'result':'0x38'},{'error':{'code':-32601,'message':'unsupported'}},RuntimeError('offline')])
    result=probe.probe(meter,rpc,{},tmp_path/'probe',tmp_path)
    assert result['status']=='NO_TRACE' and result['requests']==3
    assert [r['method'] for r in result['attempts']]==['debug_traceTransaction','trace_transaction']
    from benchmark.research_protocol import read_bound
    assert json.loads(read_bound(result['raw_requests'][1],tmp_path))['response']['error']['message']=='unsupported'


def test_parity_fallback_is_validated_and_uses_only_four_requests(tmp_path):
    rpc,tree=canonical();tx=rpc['transaction']
    parity=[{'transactionHash':probe.TX,'blockHash':tx['blockHash'],'blockNumber':16,'transactionPosition':2,'traceAddress':[],'type':'call','subtraces':0,'action':{'callType':'call','from':tx['from'],'to':tx['to'],'input':tx['input'],'value':'0x0'},'result':{'gasUsed':'0x5208','output':'0x'}}]
    meter=RPC([{'result':'0x38'},{'error':{'code':-32601}}, {'result':parity},{'result':rpc['receipt']}])
    result=probe.probe(meter,rpc,{},tmp_path/'probe',tmp_path)
    assert result['status']=='CAPTURED' and result['requests']==4
    assert result['method']=='trace_transaction'


def test_receipt_mismatch_cannot_be_counted_as_capture(tmp_path):
    rpc,tree=canonical();receipt=dict(rpc['receipt'],blockHash='0x'+'cd'*32)
    meter=RPC([{'result':'0x38'},{'result':tree},{'result':receipt}])
    result=probe.probe(meter,rpc,{},tmp_path/'probe',tmp_path)
    assert result['status']=='RECEIPT_UNVERIFIED' and 'artifact' not in result

@pytest.mark.parametrize('status,expected',[(403,403),(429,429),(True,None),('403',None),(99,None),(600,None)])
def test_probe_only_persists_valid_integer_http_status(tmp_path,status,expected):
    rpc,_=canonical()
    error=RuntimeError('DO_NOT_PERSIST_SENTINEL https://secret.invalid/token')
    error.http_status=status
    result=probe.probe(RPC([error]),rpc,{},tmp_path/'probe',tmp_path)
    from benchmark.research_protocol import read_bound
    record=json.loads(read_bound(result['raw_requests'][0],tmp_path))
    assert record.get('http_status')==expected
    assert 'DO_NOT_PERSIST_SENTINEL' not in json.dumps(record)
    assert 'secret.invalid' not in json.dumps(record)
