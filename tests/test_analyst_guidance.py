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


def test_first_checkpoint_applies_all_guidance_to_downstream_state():
    result = ForensicsResult(transaction_hash="0xexample", chain="eth")
    result.function_call_loc_memo = {'withdraw()::0xdef': [
        {'depth': [0], 'gas': 21, 'params': '', 'address': '0xdef', 'function': 'withdraw()'}]}
    feedback = AnalystFeedback(
        checkpoint="post_forensics", action="modify", modifications={
            "address_label": ["0xabc:attacker", "0xdef:victim"],
            "function_focus": ["0xdef::withdraw()"],
            "evidence_add": ["trace shows balance change"],
            "vuln_confirm": ["withdraw():confirm"],
            "attack_hypothesis": ["reentrancy via withdraw"],
        },
    )
    HumanInterface().apply_post_forensics(result, feedback)
    assert result.potential_attacker == ["0xabc"]
    assert result.potential_victim == ["0xdef"]
    assert result.functions_to_be_inspected["others"][0]["function"] == "withdraw()"
    assert result.signals["analyst_evidence"] == ["trace shows balance change"]
    assert result.signals["analyst_vulnerability_guidance"]["withdraw()"] is True
    assert result.signals["attack_hypotheses"] == ["reentrancy via withdraw"]
    from faultseeker.function_analysis.function_ranker import FunctionRanker
    ranked = FunctionRanker().rank(result, {'repeated_patterns': {},
        'function_call_loc_memo': result.function_call_loc_memo})
    assert 'withdraw()_0xdef' in ranked.functions_to_be_inspected


def test_second_checkpoint_rejection_removes_finding_and_keeps_audit_record():
    scored = [
        {"function": "withdraw()", "address": "0xabc", "confidence": {"overall": 0.9}},
        {"function": "deposit()", "address": "0xdef", "confidence": {"overall": 0.7}},
    ]
    feedback = AnalystFeedback(
        checkpoint="vulnerability_review", action="modify",
        modifications={"confirmations": {
            "withdraw()": {"confirmed": False, "note": "expected behavior"},
        }},
    )
    accepted, rejected = HumanInterface().apply_vulnerability_review(scored, feedback)
    assert [item["function"] for item in accepted] == ["deposit()"]
    assert rejected == [{"function": "withdraw()", "address": "0xabc",
                         "reason": "expected behavior"}]


def test_review_rejects_only_the_selected_contract_with_same_function_name():
    findings = [{'function':'withdraw()','address':'0xaaa'},
                {'function':'withdraw()','address':'0xbbb'}]
    feedback = AnalystFeedback(checkpoint='vulnerability_review',action='modify',
        modifications={'confirmations':{'0xaaa::withdraw()':{'confirmed':False,'note':'expected'}}})
    accepted,rejected = HumanInterface().apply_vulnerability_review(findings,feedback)
    assert accepted == [findings[1]]
    assert rejected[0]['address'] == '0xaaa'
