import copy
import unittest
from scripts.probe_train_native_opcodes import validate_native

class NativeOpcodeTests(unittest.TestCase):
 def setUp(self):
  self.tx={'hash':'0x'+'1'*64,'from':'0x'+'2'*40,'to':'0x'+'3'*40,'input':'0x12345678','value':'0x0','blockHash':'0x'+'4'*64,'blockNumber':'0x10'}
  self.receipt={'transactionHash':self.tx['hash'],'blockHash':self.tx['blockHash'],'blockNumber':'0x10','status':'0x1','gasUsed':'0x5208'}
  self.call={'from':self.tx['from'],'to':self.tx['to'],'input':self.tx['input'],'value':'0x0','type':'CALL','gasUsed':'0x5208'}
  w=lambda n:hex(n)[2:].zfill(64)
  self.op={'failed':False,'gas':21000,'structLogs':[{'depth':1,'pc':0,'op':'SLOAD','stack':[w(7)]},{'depth':1,'pc':1,'op':'POP','stack':[w(3)]},{'depth':1,'pc':2,'op':'SSTORE','stack':[w(4),w(7)]},{'depth':1,'pc':3,'op':'STOP','stack':[]}]}
 def test_actual_normalizer_on_synthetic_fixture(self):
  proof=validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash']);self.assertTrue(proof['normalization']['normalization_complete']);self.assertEqual(len(proof['normalization']['storage_events']),1);self.assertEqual(proof['normalization']['storage_events'][0]['address'],self.tx['to'])
 def test_wrong_chain_rejected(self):
  with self.assertRaises(ValueError):validate_native(1,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_wrong_hash_rejected(self):
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,'0x'+'5'*64)
 def test_wrong_gas_rejected(self):
  self.op['gas']=1
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_incomplete_frames_rejected(self):
  self.call['calls']=[{'to':'0x'+'6'*40,'type':'CALL','input':'0x'}]
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_root_calldata_mismatch_rejected(self):
  self.call['input']='0xdeadbeef'
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_receipt_hash_mismatch_rejected(self):
  self.receipt['transactionHash']='0x'+'8'*64
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_missing_storage_stack_rejected(self):
  self.op['structLogs'][2]['stack']=[]
  with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,self.op,self.tx['hash'])
 def test_failed_or_empty_trace_rejected(self):
  for change in [{'failed':True},{'structLogs':[]}]:
   op=dict(self.op,**change)
   with self.assertRaises(ValueError):validate_native(100,self.tx,self.receipt,self.call,op,self.tx['hash'])

if __name__=='__main__':unittest.main()


def test_real_native_capture_validates_and_refuses_changed_storage(tmp_path):
 import gzip,json,pytest
 from scripts.probe_train_native_opcodes import ROOT,TX,validate_recorded_native_capture
 path=ROOT/'reports/cohort_rebuild_v2/native_opcode_probe/network_continuation'/ (TX+'.json.gz')
 proof=validate_recorded_native_capture(path,TX,ROOT)
 assert proof['sload_count']==1354 and proof['sstore_count']==186
 capture=json.loads(gzip.decompress(path.read_bytes()))
 capture['normalization']['storage_reads'][0]['address']='0x'+'0'*40
 tampered=tmp_path/'altered.json.gz';tampered.write_bytes(gzip.compress(json.dumps(capture).encode()))
 with pytest.raises(ValueError,match='normalization'):
  validate_recorded_native_capture(tampered,TX,ROOT)


def test_real_native_gnosis_capture_enters_production_without_network(tmp_path,monkeypatch):
 import socket
 from scripts.probe_train_native_opcodes import ROOT,TX
 from benchmark.captured_inputs import load_train_inputs
 def forbidden(*args,**kwargs):raise AssertionError('Offline real capture must not dispatch')
 monkeypatch.setattr(socket.socket,'connect',forbidden)
 inputs=load_train_inputs(ROOT,'gnosis:'+TX)
 assert inputs.proof['identity_and_receipt_verified'] is True
 result,sequence,info=inputs.orchestrator(tmp_path/'forensics').run(TX,'gnosis')
 assert result is not None and info['receipt_identity_verified'] is True
 assert len(sequence['storage_reads'])==1354
 assert len(sequence['storage_events'])==186
 assert sequence['trace_coverage']['storage_trace_complete'] is True
 assert result.signals['reentrancy']['context']['fallback_mode'] is False
