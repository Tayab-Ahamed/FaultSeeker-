import pytest


def test_table_vi_aggregates_real_confidence_scorer_output():
    from benchmark.paper_experiments import summarize_confidence_categories
    from faultseeker.core.confidence_scorer import ConfidenceScorer
    score = ConfidenceScorer().score_function(
        {'function':'withdraw','evidence':['reentrancy callback'],'confidence_score':[0.8]},
        {'reentrancy_detected':True}).to_dict()
    row = {'identity':'eth:tx','function_identity':'address:withdraw','category':'reentrancy','confidence':score}
    result = summarize_confidence_categories([row])
    assert result['reentrancy']['C_f'] == pytest.approx(score['overall'])
    assert result['reentrancy']['PMS'] == score['components']['pattern_match']
    assert result['reentrancy']['n_functions'] == 1


def test_table_vi_refuses_missing_components_and_duplicate_functions():
    from benchmark.paper_experiments import summarize_confidence_categories
    row = {'identity':'eth:tx','function_identity':'address:f','category':'x',
           'confidence':{'overall':0.5,'components':{}}}
    with pytest.raises(ValueError,match='component'):
        summarize_confidence_categories([row])
    row['confidence']['components'] = dict.fromkeys(
        ['pattern_match','code_evidence','txn_consistency','llm_confidence'],0.5)
    with pytest.raises(ValueError,match='Duplicate'):
        summarize_confidence_categories([row,row])
