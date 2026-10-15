import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmark.verified_source_inputs import VerifiedSourceDownloader

class VerifiedSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        def put(name,data):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(data).encode('utf-8');path.write_bytes(raw)
            return {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
        self.put=put;self.address='0x'+'a'*40;self.tx='0x'+'b'*64
        self.pre=put('pre.json',{'transaction_hash':self.tx,'chain':'eth','response':{'result':{self.address:{'code':'0x6000'}}}})
        self.data={'address':self.address,'chainId':'1','runtimeMatch':'exact_match','runtimeBytecode':{'onchainBytecode':'0x6000'},'abi':[{'type':'function','name':'balanceOf','inputs':[{'type':'address'}]},{'type':'function','name':'foo','inputs':[]}],'sources':{'C.sol':{'content':'pragma solidity ^0.8.0; contract C {}'}}}
        self.response=put('response.json',self.data)
        self.evidence={'cases':[{'identity':'eth:'+self.tx,'prestate':self.pre,'contracts':[{'address':self.address,'response':self.response}],'function_evidence':[{'secret_expected_target':'foo'}]}]}
        self.binding=put('evidence.json',self.evidence)
        self.row={'chain':'eth','txn_hash':self.tx,'prestate':self.pre}
        self.split={'train_ids':['eth:'+self.tx]}
        (self.root/'benchmark').mkdir();(self.root/'benchmark/eval_split.json').write_text(json.dumps(self.split),encoding='utf-8')
    def adapter(self,addresses=None):
        with patch('benchmark.verified_source_inputs.load_train',return_value=[self.row]):
            return VerifiedSourceDownloader('eth',addresses or [self.address],root=self.root,evidence_binding=self.binding,train_identity='eth:'+self.tx)
    def test_all_abi_functions_have_actual_bundle(self):
        adapter=self.adapter();result=adapter.run();self.assertEqual(set(result[self.address]),{'0x70a08231','0xc2985578'})
        self.assertEqual(result[self.address]['0x70a08231'][0],{'path':'C.sol','content':self.data['sources']['C.sol']['content']})
        self.assertNotIn('secret_expected_target',json.dumps(result))
        self.assertEqual(adapter.provenance[self.address]['source_scope'],'full_compilation_source_bundle_not_function_slice')
    def test_source_metadata_digest_mismatch_rejected(self):
        self.data['metadata']={'sources':{'C.sol':{'keccak256':'0x'+'0'*64}}}
        self.response=self.put('response.json',self.data)
        self.evidence['cases'][0]['contracts'][0]['response']=self.response;self.binding=self.put('evidence.json',self.evidence)
        with self.assertRaises(ValueError): self.adapter().run()
    def test_output_mutation_does_not_change_subsequent_reads(self):
        adapter=self.adapter();first=adapter.run();first[self.address]['0x70a08231'][0]['content']='tampered'
        self.assertEqual(adapter.run()[self.address]['0x70a08231'][0]['content'],self.data['sources']['C.sol']['content'])
    def test_prestate_binding_tampering_rejected(self):
        (self.root/'pre.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError): self.adapter().run()
    def test_unknown_address_unavailable(self):
        unknown='0x'+'c'*40;self.assertEqual(self.adapter([unknown]).run(),{unknown:{}})
    def test_tampered_response_fails(self):
        (self.root/'response.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError): self.adapter().run()
    def test_historical_mismatch_fails_without_status_trust(self):
        self.data['runtimeBytecode']['onchainBytecode']='0x6001';self.response=self.put('response.json',self.data)
        self.evidence['cases'][0]['contracts'][0]['response']=self.response;self.binding=self.put('evidence.json',self.evidence)
        with self.assertRaises(ValueError): self.adapter().run()
    def test_nontrain_identity_rejected(self):
        self.split['train_ids']=[];(self.root/'benchmark/eval_split.json').write_text(json.dumps(self.split),encoding='utf-8')
        with self.assertRaises(ValueError): self.adapter()

if __name__=='__main__':unittest.main()
