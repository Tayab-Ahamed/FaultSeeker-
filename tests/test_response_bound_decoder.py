import hashlib
import json
import unittest
from scripts.research.response_bound_decoder import decode, signature_selector


class DecoderTests(unittest.TestCase):
    def page(self, selector, entries, next_page=None):
        body=json.dumps({'count':len(entries),'results':entries,'next':next_page})
        return {'url':'https://www.4byte.directory/api/v1/signatures/?hex_signature='+selector,
                'status':200,'retrieved_at':'2026-10-19T00:00:00Z','body':body,
                'body_sha256':hashlib.sha256(body.encode()).hexdigest()}

    def test_ethereum_selector_and_lowest_id(self):
        selector='0xa9059cbb'
        self.assertEqual(signature_selector('transfer(address,uint256)'),selector)
        entries=[{'id':8,'text_signature':'transfer(address,uint256)'},
                 {'id':2,'text_signature':'transfer(address,uint256)'},
                 {'id':0,'text_signature':'approve(address,uint256)'}]
        result=decode(selector,[self.page(selector,entries)])
        self.assertEqual(result['selector'],selector)
        self.assertEqual(result['decoded_name'],'transfer')
        self.assertEqual(result['registry_id'],2)
        self.assertFalse(result['verified_abi'])

    def test_bad_binding_and_incomplete_pages_are_empty(self):
        selector='0xa9059cbb'
        page=self.page(selector,[{'id':2,'text_signature':'transfer(address,uint256)'}])
        page['body_sha256']='0'*64
        self.assertEqual(decode(selector,[page])['decoded_name'],'')
        page=self.page(selector,[],next_page='https://www.4byte.directory/api/v1/signatures/?page=2&hex_signature='+selector)
        self.assertEqual(decode(selector,[page])['decoded_name'],'')
        self.assertEqual(decode(selector,[])['decoded_name'],'')
        page=self.page(selector,[{'id':2,'text_signature':'transfer(address,uint256)'}])
        page['url'] += '&page=2'
        self.assertEqual(decode(selector,[page])['decoded_name'],'')

    def test_malformed_and_nonmatching_signatures_rejected(self):
        selector='0xa9059cbb'
        page=self.page(selector,[{'id':1,'text_signature':'transfer(address, uint256)'},
                                 {'id':2,'text_signature':'approve(address,uint256)'}])
        self.assertEqual(decode(selector,[page])['decoded_name'],'')
