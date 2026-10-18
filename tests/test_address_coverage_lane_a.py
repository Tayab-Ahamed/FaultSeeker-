import copy
import unittest
from scripts.research.address_coverage_lane_a import extract_candidates, rank_candidates, FEATURES
from scripts.research.evaluate_coverage_lane_a import fit

A='0x'+'a'*40
B='0x'+'b'*40
C='0x'+'c'*40

class CoverageTests(unittest.TestCase):
    def test_poisoned_labels_ignored(self):
        p=dict(code_address=A,function='withdraw()',count=1,supporting_call_depths=[[0]])
        poisoned=dict(p,target=B,score=999,correct=True,incident='target',source_url=B)
        self.assertEqual(extract_candidates([p],''),extract_candidates([poisoned],''))
        self.assertEqual(set(extract_candidates([p],'')[0]),set(FEATURES)|{'address'})
    def test_trace_calls_proxy_and_event(self):
        trace=f'[1] {A}::run()\n    ├─ [2] {B}::doIt() [delegatecall]\n    │   ├─ emit Transfer(to: {C})'
        rows=extract_candidates([],trace)
        self.assertEqual([r['address'] for r in rows],[A,B,C])
        self.assertEqual(rank_candidates(rows,{'kind':'call_append'}),[A,B])
        self.assertGreater(rows[0]['trace_delegate'],0)
        self.assertGreater(rows[2]['trace_event_references'],0)
    def test_warnings_hash_zero_excluded(self):
        trace=f'Warning: {A}\n emit Transfer(to: 0x'+ '0'*40 +', hash: 0x'+'c'*64+')'
        self.assertEqual(extract_candidates([],trace),[])
    def test_heldout_labels_do_not_affect_fit(self):
        evidence=extract_candidates([dict(code_address=A,function='f()',count=1)],f'{B}::g()')
        rows=[dict(coverage_evidence=evidence,targets=[A]),dict(coverage_evidence=evidence,targets=[B])]
        before=fit(rows,[0])
        rows[1]['targets']=[C]
        self.assertEqual(before,fit(rows,[0]))

if __name__=='__main__':
    unittest.main()
