"""Offline acceptance tests for the preregistered distinct EOA controls."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from scripts import acquire_distinct_benign_controls as controls


def fixture():
    tx = {'hash': '0x'+'ab'*32, 'from': '0x'+'11'*20, 'to': '0x'+'22'*20,
          'value': '0x1', 'input': '0x', 'chainId': '0x1', 'type': '0x2',
          'blockHash': '0x'+'cd'*32, 'blockNumber': '0xe04dc0', 'transactionIndex': '0x0'}
    block = {'hash': tx['blockHash'], 'number': tx['blockNumber'], 'parentHash': '0x'+'ef'*32,
             'transactions': [tx]}
    receipt = {'transactionHash': tx['hash'], 'blockHash': block['hash'],
               'blockNumber': block['number'], 'transactionIndex': '0x0', 'status': '0x1', 'logs': []}
    return tx, block, receipt


def test_complete_control_requires_canonical_receipt_and_all_explicit_code_observations():
    tx, block, receipt = fixture()
    assert controls.eligibility(tx, block, receipt, ['0x','0x','0x'], set(), set(), set()) == []
    for codes in ([None,'0x','0x'], ['0x','0x01','0x'], ['0x','0x',None]):
        assert controls.eligibility(tx, block, receipt, codes, set(), set(), set())
    receipt['transactionIndex'] = '0x1'
    assert 'CANONICAL_RECEIPT_MISMATCH' in controls.eligibility(tx, block, receipt, ['0x']*3, set(), set(), set())


@pytest.mark.parametrize('field,value,reason', [('value','0x0','NONPOSITIVE_VALUE'),
    ('input','0x00','NONEMPTY_INPUT'), ('to','0x'+'00'*19+'01','PRECOMPILE_OR_RESERVED_DESTINATION'),
    ('chainId','0x38','CHAIN_ID_MISMATCH')])
def test_cheap_exclusion_is_explicit(field,value,reason):
    tx, block, receipt = fixture(); tx[field]=value
    assert reason in controls.eligibility(tx,block,receipt,['0x']*3,set(),set(),set())


def test_duplicate_hash_sender_and_recipient_are_rejected():
    tx,block,receipt=fixture()
    reasons=controls.eligibility(tx,block,receipt,['0x']*3,{tx['hash']},{tx['from']},{tx['to']})
    assert {'DUPLICATE_HASH','REUSED_SENDER','REUSED_RECIPIENT'} <= set(reasons)


def test_receipt_failure_and_logs_are_rejected():
    tx,block,receipt=fixture();receipt.update(status='0x0',logs=[{}])
    assert {'RECEIPT_NOT_SUCCESS','NONEMPTY_LOGS'} <= set(controls.eligibility(tx,block,receipt,['0x']*3,set(),set(),set()))


def test_live_entry_requires_opt_in_before_any_credentials_or_rpc(tmp_path):
    with pytest.raises(ValueError,match='live'):
        controls.run_live(root=tmp_path)


def test_acquisition_binds_raw_records_and_uses_exact_hash_tags(tmp_path):
    tx,block,receipt=fixture(); n=int(block['number'],16)
    class RPC:
        count=0
        def forward(self,payload):
            self.count+=1
            method,params=payload['method'],payload['params']
            if method=='eth_chainId': result='0x1'
            elif method=='eth_getBlockByNumber': result=block
            elif method=='eth_getBlockByHash': result={'hash':block['parentHash'],'number':hex(n-1)}
            elif method=='eth_getTransactionReceipt': result=receipt
            elif method=='eth_getCode':
                assert params[1] in ({'blockHash':block['hash'],'requireCanonical':True}, {'blockHash':block['parentHash'],'requireCanonical':True})
                result='0x'
            elif method=='debug_traceTransaction': result={'type':'CALL','from':tx['from'],'to':tx['to'],'input':'0x','value':'0x1','gasUsed':'0x5208','output':'0x'}
            else: raise AssertionError(method)
            return {'jsonrpc':'2.0','id':payload['id'],'result':result}
        def summary(self): return {'outbound_rpc_requests':self.count}
    prereg={'schema':1,'study':controls.STUDY,'target_count':32,'chain':'eth','chain_id':1,'block_numbers':[n]}
    summary=controls.acquire(RPC(),prereg,tmp_path/'benign_controls',tmp_path)
    assert summary['accepted_count']==1
    assert summary['status']=='INCOMPLETE'
    binding=summary['accepted'][0]['record']
    import hashlib
    raw=(tmp_path/binding['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==binding['sha256']
    record=json.loads(raw)
    assert len(record['requests'])==5
    assert record['call_trace']['available'] is True

def test_fixed_selection_caps_four_per_block_and_stops_at_32(tmp_path):
    class RPC:
        count=0
        def forward(self,payload):
            self.count+=1;method,params=payload['method'],payload['params']
            if method=='eth_chainId':value='0x1'
            elif method=='eth_getBlockByNumber':
                n=int(params[0],16); self.block={'number':hex(n),'hash':'0x'+format(n,'064x'),'parentHash':'0x'+format(n-1,'064x'),'transactions':[]}
                for i in range(8):
                    uid=n*10+i
                    self.block['transactions'].append({'hash':'0x'+format(uid,'064x'),'from':'0x'+format(uid,'040x'),'to':'0x'+format(uid+10**9,'040x'),'value':'0x1','input':'0x','chainId':'0x1','type':'0x2','blockHash':self.block['hash'],'blockNumber':hex(n),'transactionIndex':hex(i)})
                value=self.block
            elif method=='eth_getBlockByHash':value={'hash':params[0],'number':hex(int(params[0],16))}
            elif method=='eth_getTransactionReceipt':
                tx=next(t for t in self.block['transactions'] if t['hash']==params[0]);value={'transactionHash':tx['hash'],'blockHash':tx['blockHash'],'blockNumber':tx['blockNumber'],'transactionIndex':tx['transactionIndex'],'status':'0x1','logs':[]}
            elif method=='eth_getCode':value='0x'
            elif method=='debug_traceTransaction':return {'error':{'code':-32601,'message':'secret'}}
            else:raise AssertionError(method)
            return {'result':value}
        def summary(self):return {'outbound_rpc_requests':self.count}
    report=controls.acquire(RPC(),{'block_numbers':controls.BLOCKS,'target_count':32},tmp_path/'out',tmp_path)
    assert report['status']=='COMPLETE' and report['accepted_count']==32
    assert len(report['blocks'])==8
    assert all(b['accepted']==4 for b in report['blocks'])
    assert report['outbound_logical_requests']==177
    assert len({r['transaction_hash'] for r in report['accepted']})==32
    assert 'secret' not in ''.join(p.read_text() for p in (tmp_path/'out').rglob('*.json'))


def test_budget_exhaustion_preserves_last_inspected_candidate(tmp_path,monkeypatch):
    monkeypatch.setattr(controls,'MAX_REQUESTS',6)
    tx,block,receipt=fixture(); n=int(block['number'],16)
    class RPC:
        def forward(self,p):
            m=p['method'];value={'eth_chainId':'0x1','eth_getBlockByNumber':block,'eth_getBlockByHash':{'hash':block['parentHash'],'number':hex(n-1)}}[m]
            return {'result':value}
        def summary(self):return {}
    report=controls.acquire(RPC(),{'block_numbers':[n],'target_count':32},tmp_path/'out',tmp_path)
    assert report['stop_reason']=='REQUEST_BOUND_REACHED'
    assert report['candidates'][0]['reasons']==['REQUEST_BOUND_BEFORE_ELIGIBILITY']
