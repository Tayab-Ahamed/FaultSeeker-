import math
import pytest
from faultseeker.research.calibration import LogisticConfidenceCalibrator, FEATURE_NAMES
from faultseeker.core.confidence_scorer import ConfidenceScorer


def test_legacy_proxy_model_cannot_calibrate_production_factors():
    model = LogisticConfidenceCalibrator()
    model.fit([{k: .1 for k in FEATURE_NAMES}, {k: .9 for k in FEATURE_NAMES}], [0, 1], epochs=2)
    with pytest.raises(ValueError, match='schema'):
        model.require_schema('production-confidence-v1')


def test_schema_and_training_provenance_survive_save_load(tmp_path):
    model = LogisticConfidenceCalibrator()
    rows = [{k: value for k in FEATURE_NAMES} for value in (.2, .4, .6, .8)]
    model.fit_observations(rows, [0, 0, 1, 1], ['a', 'b', 'c', 'd'], ['e', 'f'], epochs=2)
    path = tmp_path / 'model.json'
    model.save(str(path))
    restored = LogisticConfidenceCalibrator.load(str(path))
    restored.require_schema('production-confidence-v1')
    assert restored.training_ids == ['a', 'b', 'c', 'd']
    assert restored.evaluation_ids == ['e', 'f']
    assert restored.predict_proba(rows[0]) == model.predict_proba(rows[0])


def test_overlapping_training_and_evaluation_ids_are_rejected():
    model = LogisticConfidenceCalibrator()
    rows = [{k: .2 for k in FEATURE_NAMES}, {k: .8 for k in FEATURE_NAMES}]
    with pytest.raises(ValueError, match='overlap'):
        model.fit_observations(rows, [0, 1], ['a', 'b'], ['b'], epochs=2)


def test_nonfinite_feature_cannot_become_probability():
    model = LogisticConfidenceCalibrator()
    with pytest.raises(ValueError, match='finite'):
        model.predict_proba({'pattern_match': float('nan')})


def test_paper_formula_remains_a_relative_score():
    scorer = ConfidenceScorer()
    result = scorer.score_function({'evidence': ['reentrancy'], 'confidence_score': [0.8]}, {})
    expected = (.30 * result.pattern_match + .25 * result.code_evidence +
                .25 * result.txn_consistency + .20 * result.llm_confidence)
    assert math.isclose(result.overall, expected)
    assert result.to_dict()['score_semantics'] == 'heuristic-relative-ranking'


def test_export_and_inference_use_the_same_observed_depth_and_storage_features():
    from benchmark.export_research_features import features_from_result
    from faultseeker.research.calibration import production_features
    components = dict(pattern_match=.1,code_evidence=.2,txn_consistency=.3,llm_confidence=.4)
    signals = {'trace_entropy':.5,'token_flow_anomaly':.6,
               'debug':{'call_depth_max':7,'storage_events_total':8}}
    inference = production_features(components,signals)
    exported = features_from_result({'scored_functions':[{'confidence':{'components':components}}],
                                     'signals':signals},1)
    assert inference == {key:exported[key] for key in FEATURE_NAMES}
    assert inference['call_depth'] == 7
    assert inference['state_delta'] == 8
    with pytest.raises(ValueError,match='genuine'):
        features_from_result({'scored_functions':[]},1)


def test_nonfinite_model_confidence_never_becomes_high_confidence():
    score = ConfidenceScorer()._compute_llm_confidence({'confidence_score':[float('nan'),float('inf'),.8]})
    assert score == .8
