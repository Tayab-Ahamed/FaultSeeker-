import unittest
from scripts.research.names_semantics import tokens, documents


class NamesTests(unittest.TestCase):
    def test_identifiers_only(self):
        self.assertEqual(tokens('withdrawAll(uint256,address)'), ['withdraw', 'all'])
        self.assertEqual(tokens('0x12345678'), [])
        self.assertEqual(tokens('0x' + 'a' * 40), [])
        self.assertEqual(tokens('https://incident.example/'), [])

    def test_unknown_fields_ignored(self):
        address = '0x' + 'a' * 40
        p = {'code_address': address, 'function': 'deposit()'}
        before = documents([address], [p], '')
        p.update(target='exploit', incident='hack', function_gt='steal', score=100)
        self.assertEqual(before, documents([address], [p], ''))
        self.assertEqual(before, ['deposit'])
