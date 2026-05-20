from faultseeker.forensics.interaction_graph import TransactionInteractionGraph
from faultseeker.research.adversarial import AdversarialRobustnessEvaluator
from faultseeker.research.calibration import LogisticConfidenceCalibrator
from faultseeker.research.statistics import (
    bootstrap_ci,
    mcnemar_test,
    paired_t_test,
    wilcoxon_signed_rank,
)


def test_logistic_calibrator_trains_and_reports_calibration_metrics():
    rows = [
        {"pattern_match": 0.1, "code_evidence": 0.2, "txn_consistency": 0.1, "llm_confidence": 0.2},
        {"pattern_match": 0.2, "code_evidence": 0.2, "txn_consistency": 0.3, "llm_confidence": 0.4},
        {"pattern_match": 0.8, "code_evidence": 0.7, "txn_consistency": 0.9, "llm_confidence": 0.8},
        {"pattern_match": 0.9, "code_evidence": 0.8, "txn_consistency": 0.7, "llm_confidence": 0.9},
    ]
    labels = [0, 0, 1, 1]

    model = LogisticConfidenceCalibrator().fit(rows, labels, epochs=120)
    low = model.predict_proba(rows[0])
    high = model.predict_proba(rows[-1])
    metrics = model.evaluate(rows, labels, bins=4)

    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0
    assert high > low
    assert 0.0 <= metrics.brier_score <= 1.0
    assert 0.0 <= metrics.expected_calibration_error <= 1.0


def test_transaction_interaction_graph_extracts_motifs_and_metrics():
    tx_analysis = {
        "trace": {
            "address": "0xA",
            "function": "entry",
            "children": [
                {
                    "address": "0xB",
                    "function": "delegate",
                    "call_type": "delegatecall",
                    "children": [{"address": "0xA", "function": "callback", "call_type": "call", "children": []}],
                }
            ],
        },
        "storage_events": [{"address": "0xA", "slot": "0x01", "depth": 1}],
    }
    txn_info = {"token_transfer": {"edges": [{"source": "0xA", "target": "0xB", "label": "TOKEN (10)"}]}}

    metrics = TransactionInteractionGraph.from_analysis({}, tx_analysis, txn_info).metrics()

    assert metrics["node_count"] >= 3
    assert metrics["delegatecall_edges"] == 1
    assert metrics["storage_slot_edges"] == 1
    assert "proxy_delegatecall" in metrics["motifs"]
    assert metrics["anomaly_score"] > 0


def test_adversarial_evaluator_generates_attack_variants_and_degradation_report():
    evaluator = AdversarialRobustnessEvaluator()
    tx_analysis = {"trace": {"function": "withdraw", "call_type": "call", "children": []}}

    def analyzer(data):
        function_name = data["trace"].get("function", "")
        return {"priority_score": 0.8 if function_name == "withdraw" else 0.4}

    report = evaluator.evaluate(tx_analysis, analyzer)

    assert report["baseline_score"] == 0.8
    assert "misleading_function_names" in report["attacks"]
    assert report["attacks"]["misleading_function_names"]["degraded"] is True


def test_statistical_helpers_return_reproducible_values():
    values = [0.7, 0.8, 0.9, 0.85]
    low, high = bootstrap_ci(values, samples=100, seed=7)
    t = paired_t_test([0.9, 0.8, 0.7], [0.7, 0.7, 0.6])
    w = wilcoxon_signed_rank([0.9, 0.8, 0.7], [0.7, 0.7, 0.6])
    m = mcnemar_test([True, True, False, False], [True, False, True, False])

    assert low <= high
    assert t["n"] == 3
    assert w["n"] == 3
    assert m["b01"] == 1
    assert m["b10"] == 1
