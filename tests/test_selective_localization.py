from scripts.research.evaluate_selective_localization import (
    aggregate_metrics,
    evidence_features,
    split_for_group,
)


def row(score, first_rank):
    return {
        "prediction_time_features": {"score": score},
        "baseline_first_hit_rank": first_rank,
    }


def test_metrics_use_first_hit_rank_for_each_recall_denominator():
    metrics = aggregate_metrics([row(0.9, 1), row(0.8, 3), row(0.1, None)], None)

    assert metrics["eligible_n"] == 3
    assert metrics["predicted_n"] == 3
    assert metrics["hits"] == {"1": 1, "3": 2, "5": 2}
    assert metrics["recall"] == {"1": 1 / 3, "3": 2 / 3, "5": 2 / 3}


def test_abstention_removal_counts_correctness_at_each_k():
    metrics = aggregate_metrics([row(0.9, 1), row(0.8, 3), row(0.1, None)], 0.5)

    assert metrics["predicted_n"] == 2
    assert metrics["abstained_n"] == 1
    assert metrics["hits"] == {"1": 1, "3": 2, "5": 2}


def test_evidence_features_do_not_require_ground_truth_fields():
    features = evidence_features(
        {
            "predictions": [
                {
                    "code_address": "0x" + "a" * 40,
                    "function": "withdraw",
                    "count": 2,
                    "supporting_call_depths": [[0, 1]],
                    "selector": None,
                }
            ],
            "cast": {"output_tail": ""},
        }
    )

    assert features["candidate_available"] is True
    assert features["trace_available"] is False
    assert features["no_trace_output"] is True
    assert "ground_truth" not in features
    assert "target" not in features


def test_group_split_is_deterministic():
    first = split_for_group("0x" + "a" * 40)
    second = split_for_group("0x" + "a" * 40)

    assert first == second
    assert first[0] in {"train", "validation", "test"}
