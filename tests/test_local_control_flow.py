"""Local control-flow contracts for deterministic triage and analyst review."""

import pytest

from faultseeker.core.config import FaultSeekerConfig
from faultseeker.core.human_interface import AnalystFeedback, HumanInterface
from faultseeker.core.pipeline import FaultSeekerPipeline
from faultseeker.forensics.fund_flow_analyzer import FundFlowAnalyzer
from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from faultseeker.forensics.result import ForensicsResult
from faultseeker.forensics.rule_classifier import classify
from faultseeker.forensics.signal_extractor import SignalBundle
from faultseeker.research.calibration import FEATURE_NAMES, LogisticConfidenceCalibrator




def test_clean_signals_need_explicit_complete_coverage_to_be_benign():
    incomplete = SignalBundle(raw={"coverage": {"trace_complete": True}})
    assert classify(incomplete)[0] == "UNCERTAIN"

    complete = SignalBundle(raw={"coverage": {
        "trace_complete": True,
        "token_flow_complete": True,
        "multi_tx_context_complete": True,
    }})
    verdict, confidence, rule, _ = classify(complete)
    assert (verdict, rule) == ("BENIGN", "complete_clean_coverage")
    assert confidence >= 0.85








def test_explicit_legacy_calibrator_cannot_be_used_as_production_probability(tmp_path):
    model = LogisticConfidenceCalibrator()
    model.fit([{key: 0.0 for key in FEATURE_NAMES},
               {key: 1.0 for key in FEATURE_NAMES}], [0, 1], epochs=1)
    path = tmp_path / "legacy.json"
    model.save(str(path))
    with pytest.raises(ValueError, match="schema"):
        FaultSeekerPipeline._load_calibrator(str(path))








def test_pipeline_bypasses_stage_two_before_model_setup_for_proven_benign(tmp_path):
    class StageOne:
        def run(self, txn_hash, chain):
            return (ForensicsResult(
                transaction_hash=txn_hash, chain=chain,
                rule_verdict="BENIGN", rule_confidence=0.9,
                matched_rule="complete_clean_coverage",
                signals={"coverage": {"trace_complete": True,
                                      "token_flow_complete": True,
                                      "multi_tx_context_complete": True}},
            ), {}, {})

    pipeline = FaultSeekerPipeline(
        FaultSeekerConfig(cache_dir=str(tmp_path)),
        forensics_orchestrator=StageOne(),
    )
    outcome = pipeline.analyze_transaction(txn_hash="0xexample", chain="eth")
    assert outcome["verdict"] == "BENIGN"
    assert outcome["stage2_bypassed"] is True
    assert pipeline.function_analyzer is None
    assert outcome["scored_functions"] == []


def test_pipeline_stage_two_rejection_updates_final_findings(tmp_path):
    class StageOne:
        def run(self, txn_hash, chain):
            return (ForensicsResult(transaction_hash=txn_hash, chain=chain,
                                    rule_verdict="UNCERTAIN", rule_confidence=0.4,
                                    repeated_patterns={"keys": [], "keys_function_only": []}), {}, {})

    class Ranker:
        def rank(self, *args):
            return type("Ranking", (), {"address_list": []})()

    class Analyzer:
        def run(self, *args):
            return {"finalized_vulnerable_functions": [
                {"function": "withdraw()", "address": "0xabc", "evidence": ["call trace"]},
            ], "potentially_vulnerable_functions": {
                'withdraw()_0xabc': {'evidence': ['call trace'], 'depth': 1},
            }, "duration": 0.1}

    class Reviewer(HumanInterface):
        def checkpoint_vulnerability_review(self, scored_functions):
            feedback = AnalystFeedback(
                checkpoint="vulnerability_review", action="modify",
                modifications={"confirmations": {"withdraw()": {
                    "confirmed": False, "note": "reviewed as benign"}}},
            )
            self.feedback_log.append(feedback)
            return feedback

    pipeline = FaultSeekerPipeline(
        FaultSeekerConfig(cache_dir=str(tmp_path)),
        forensics_orchestrator=StageOne(), function_ranker=Ranker(),
        function_analyzer=Analyzer(), human_interface=Reviewer(),
    )
    outcome = pipeline.analyze_transaction(txn_hash="0xexample", chain="eth")
    assert outcome["scored_functions"] == []
    assert outcome["evidence_cards"] == []
    assert outcome["potentially_vulnerable_functions"] == []
    assert outcome["rejected_findings"] == [{
        "function": "withdraw()", "address": "0xabc", "reason": "reviewed as benign"}]
    assert outcome["analyst_feedback"][1]["action"] == "modify"
