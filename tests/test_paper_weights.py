import pytest
from faultseeker.core.paper_profile import score_reentrancy


@pytest.mark.parametrize('signal,expected',[
    ('repeated_slot_nested',.55),('write_after_external_call',.25),
    ('same_function_reentered',.20),('write_before_and_after',.10),('same_slot_rewritten',.10)])
def test_each_paper_weight_contributes_to_the_executed_score(signal,expected):
    assert score_reentrancy({signal:True},fallback=False) == expected


def test_storage_score_clamps_the_actual_one_point_two_sum():
    assert score_reentrancy({key:True for key in ('repeated_slot_nested','write_after_external_call',
        'same_function_reentered','write_before_and_after','same_slot_rewritten')},False) == 1.
