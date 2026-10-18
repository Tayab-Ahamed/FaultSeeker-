import unittest
from scripts.research.names_semantics_corrected import tokens, documents


class CorrectedNamesTests(unittest.TestCase):
    def test_bare_selector_variants_never_become_words(self):
        for value in ('deadbeef', 'aaa94bfa', 'DEADBEEF', 'deadbeef()', '0xdeadbeef', '12345678'):
            self.assertEqual(tokens(value), [], value)
        self.assertEqual(tokens('withdrawAll(uint256)'), ['withdraw', 'all'])

    def test_bare_selector_rejected_in_prediction_and_trace(self):
        address = '0x' + 'a' * 40
        predictions = [{'code_address': address, 'function': 'aaa94bfa'}]
        trace = f'[1] {address}::deadbeef()'
        self.assertEqual(documents([address], predictions, trace), [''])
