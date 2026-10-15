import unittest
from scripts.acquire_train_localization_sources import abi_signature, verified_contract, trace_matches

class LocalizationEvidenceTests(unittest.TestCase):
    def test_nested_tuple_signature(self):
        entry={'name':'f','inputs':[{'type':'tuple[]','components':[{'type':'address'},{'type':'uint256'}]},{'type':'bytes32'}]}
        self.assertEqual(abi_signature(entry),'f((address,uint256)[],bytes32)')
    def test_identity_requires_historical_exact_match(self):
        data={'address':'0x'+'a'*40,'chainId':'1','runtimeMatch':'exact_match','runtimeBytecode':{'onchainBytecode':'0x6000'},'abi':[]}
        self.assertTrue(verified_contract(data,'0x'+'a'*40,'0x6000'))
        self.assertFalse(verified_contract(data,'0x'+'a'*40,'0x6001'))
        data['runtimeMatch']=None
        self.assertFalse(verified_contract(data,'0x'+'a'*40,'0x6000'))
    def test_delegate_keeps_storage_owner(self):
        tree={'to':'0x'+'a'*40,'type':'CALL','input':'0x12345678','calls':[{'to':'0x'+'b'*40,'type':'DELEGATECALL','input':'0x12345678'}]}
        result=trace_matches(tree,'0x'+'b'*40,'0x12345678')
        self.assertEqual(result[0]['storage_address'],'0x'+'a'*40)
        self.assertEqual(result[0]['code_address'],'0x'+'b'*40)
        self.assertEqual(result[0]['call_type'],'DELEGATECALL')
    def test_wrong_selector_not_accepted(self):
        self.assertEqual(trace_matches({'to':'0x'+'a'*40,'input':'0xdeadbeef'},'0x'+'a'*40,'0x12345678'),[])

if __name__=='__main__': unittest.main()
