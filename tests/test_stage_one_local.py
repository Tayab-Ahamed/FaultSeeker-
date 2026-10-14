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


def test_default_configuration_can_start_without_cloud_credentials(monkeypatch, tmp_path):
    for name in ("OPENAI_API_KEY", "XAI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    config = FaultSeekerConfig(cache_dir=str(tmp_path))
    assert config.forensics_model == "gpt-4o-mini"


def test_fund_flow_analysis_is_deterministic_and_keyless():
    info = {
        "transaction_hash": "0xexample",
        "address_info": {"from_address": "0xsender", "to_address": ["0xpool"]},
        "token_transfer": {"edges": [
            {"source": "0xpool", "target": "0xreceiver", "label": "0xtoken [TOKEN] (12)"},
        ]},
    }
    analysis = FundFlowAnalyzer().run(info)
    assert analysis["balance_change"]["0xpool"]["0xtoken"]["amount"] == -12
    assert analysis["potential_victim"] == ["0xpool"]
    assert "0xsender" in analysis["potential_attacker"]


def test_stage_one_constructor_does_not_build_model_agents(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise AssertionError("Stage 1 must not build a model agent")

    monkeypatch.setattr("faultseeker.forensics.orchestrator.build_agent", fail)
    monkeypatch.setattr("faultseeker.forensics.address_classifier.build_agent", fail)
    orchestrator = ForensicsOrchestrator(cache_dir=str(tmp_path))
    assert orchestrator.address_classifier is not None


def test_multi_tx_coverage_requires_recorded_context_evidence():
    txn_seq = {"trace_coverage": {"trace_complete": True,
                                  "token_flow_complete": True}}
    missing = ForensicsOrchestrator._verified_coverage(
        txn_seq, {"multi_tx_context_complete": True})
    assert missing["multi_tx_context_complete"] is False
    recorded = ForensicsOrchestrator._verified_coverage(
        txn_seq, {"multi_tx_context_complete": True,
                  "context_evidence": ["verified prior and following transactions"]})
    assert recorded == {"trace_complete": True, "token_flow_complete": True,
                        "multi_tx_context_complete": True}
