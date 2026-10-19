import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cached_upstream_evaluator_preserves_115_denominator_and_metrics(tmp_path):
    from scripts.reproduce.evaluate_original_upstream_cached import evaluate

    output = evaluate(
        ROOT / "benchmark/original_faultseeker/ground_truth",
        ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw",
        tmp_path / "result",
    )
    aggregate = output["aggregate"]
    upstream = aggregate["upstream_reconstruction"]
    assert aggregate["n_total"] == 115
    assert aggregate["n_ok"] == 110
    assert aggregate["n_failed"] == 5
    assert [upstream[field]["hits"] for field in ("recall_at_1", "recall_at_3", "recall_at_5")] == [27, 49, 53]
    assert aggregate["failure_stages"]["data_collection_or_trace_replay"] == 5
    assert aggregate["failure_stages"]["final_ranking_or_ground_truth_mismatch"] == 43
    assert len(output["rows"]) == 115
    assert (tmp_path / "result" / "evaluation.json").is_file()
    assert json.loads((tmp_path / "result" / "evaluation.json").read_text())["upstream"]["source_commit"] == "72753bd833554449efa8499f0d1775a97fb5c696"


def test_cached_upstream_evaluator_refuses_overwrite(tmp_path):
    from scripts.reproduce.evaluate_original_upstream_cached import evaluate

    output = tmp_path / "result"
    output.mkdir()
    try:
        evaluate(
            ROOT / "benchmark/original_faultseeker/ground_truth",
            ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw",
            output,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("cached evaluation overwrote an existing output")
