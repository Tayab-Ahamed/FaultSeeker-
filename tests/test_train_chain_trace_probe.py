import sys
import unittest

sys.modules['readline'] = None


class TrainChainTraceProbeTests(unittest.TestCase):
    def test_rejects_unfrozen_identity(self):
        from scripts.probe_train_chain_traces import require_train
        with self.assertRaises(ValueError):
            require_train('bsc:wrong', {'train_ids': ['bsc:other']})

    def test_total_request_cap_applies_across_endpoints(self):
        from scripts.probe_train_chain_traces import ProbeBudget
        budget = ProbeBudget(2)
        budget.take()
        budget.take()
        with self.assertRaises(RuntimeError):
            budget.take()
        self.assertEqual(budget.used, 2)

    def test_trace_identity_checks_calldata_and_value(self):
        from scripts.probe_train_chain_traces import validate_trace
        tx = {'from': '0xaa', 'to': '0xbb', 'input': '0x12', 'value': '0x1'}
        trace = {'from': '0xaa', 'to': '0xbb', 'input': '0x13', 'value': '0x1', 'type': 'CALL'}
        with self.assertRaises(ValueError):
            validate_trace(trace, tx, {})
        trace['input'] = '0x12'
        validate_trace(trace, tx, {})

    def test_sanitizes_credential_error(self):
        from scripts.probe_train_chain_traces import safe_error
        self.assertEqual(safe_error(RuntimeError('https://secret/key')), {'error_type': 'RuntimeError'})

    def test_parity_rejects_missing_child_and_wrong_block(self):
        from scripts.probe_train_chain_traces import parity_call_tree
        tx = {'hash': '0x123', 'from': '0xaa', 'to': '0xbb', 'input': '0x12', 'value': '0x0',
              'blockHash': '0xabc', 'blockNumber': '0x1', 'transactionIndex': '0x0'}
        row = {'transactionHash': '0x123', 'blockHash': '0xabc', 'blockNumber': 1,
               'transactionPosition': 0, 'traceAddress': [], 'subtraces': 0, 'type': 'call',
               'action': {'callType': 'call', 'from': '0xaa', 'to': '0xbb', 'input': '0x12', 'value': '0x0'},
               'result': {'gasUsed': '0x1', 'output': '0x'}}
        self.assertEqual(parity_call_tree([row], tx, {})['type'], 'CALL')
        row['subtraces'] = 1
        with self.assertRaises(ValueError):
            parity_call_tree([row], tx, {})
        row['subtraces'], row['blockNumber'] = 0, 2
        with self.assertRaises(ValueError):
            parity_call_tree([row], tx, {})


if __name__ == '__main__':
    unittest.main()
