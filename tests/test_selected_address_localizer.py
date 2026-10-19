from copy import deepcopy
from scripts.research import selected_address_localizer as localizer

A='0x'+'a'*40
B='0x'+'b'*40

def test_preparation_ignores_labels_and_expected_scores():
    predictions=[{'code_address':A,'function':'withdrawAll(uint256)','count':2,'supporting_call_depths':[[0,1],[0,2]]}]
    original=localizer.prepare(predictions,'')
    poison=deepcopy(predictions);poison[0].update(target=B,expected_rank=1,score=999,correct=True)
    assert localizer.prepare(poison,'')==original

def test_rank_keeps_learned_prefix_and_appends_observed_addresses():
    predictions=[{'code_address':A,'function':'withdraw()','count':1,'supporting_call_depths':[[0]]}]
    row=localizer.prepare(predictions,f'[1] {B}::deposit()')
    assert localizer.append_observed([A],row)==[A,B]
    assert localizer.append_observed([A,B],row)==[A,B]
