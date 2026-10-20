from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GT = ROOT / "benchmark/original_faultseeker/ground_truth"
RAW = ROOT / "reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017/raw"
EVALUATION = ROOT / "reports/original_benchmark/upstream-compatible-cached-20261019-final/evaluation.json"


def test_error_attribution_recomputes_authoritative_metrics_and_preserves_115_rows(tmp_path):
    from scripts.reproduce.analyze_original_error_attribution import analyze

    report = analyze(GT, RAW, EVALUATION, tmp_path / "attribution")
    aggregate = report["aggregate"]
    assert aggregate["n_total"] == 115
    assert aggregate["status_counts"] == {"failed": 5, "ok": 110}
    assert [aggregate["upstream_reconstruction"][f"recall_at_{k}"]["hits"] for k in (1, 3, 5)] == [27, 49, 53]
    assert [aggregate["current_address_aware"][f"recall_at_{k}"]["hits"] for k in (1, 3, 5)] == [25, 49, 52]
    assert aggregate["authoritative_comparison"]["matches"] is True
    assert len(report["rows"]) == 115


def test_error_attribution_has_each_required_evidence_bounded_case_class(tmp_path):
    from scripts.reproduce.analyze_original_error_attribution import analyze

    report = analyze(GT, RAW, EVALUATION, tmp_path / "attribution")
    by_case = {row["case_id"]: row for row in report["rows"]}
    assert by_case["0x04e16a79ff928db2fa88619cdd045cdfc7979a61d836c9c9e585b3d6f6d8bc31"]["primary_classification"] == "A_cached_execution_trace_failure"
    assert by_case["0x2881e839d4d562fad5356183e4f6a9d427ba6f475614ce8ef64dbfe557a4a2cc"]["primary_classification"] == "E_demonstrated_identity_normalization_mismatch"
    assert by_case["0x6439d63cc57fb68a32ea8ffd8f02496e8abad67292be94904c0b47a4d14ce90d"]["primary_classification"] == "D_top5_candidate_reconstruction_equality_miss"
    assert by_case["0x00c5a772a58b117f142b2cbc8721b80d145ef7a910043ad08439863d0e78e300"]["primary_classification"] == "B_no_target_candidate_in_saved_set"
    assert by_case["0xeb8c3bebed11e2e4fcd30cbfc2fb3c55c4ca166003c7f7d319e78eaab9747098"]["primary_classification"] == "C_target_candidate_ranked_outside_top5"
    assert by_case["0xe4db1550e3aa78a05e93bfd8fbe21b6eba5cce50dc06688949ab479ebed18048"]["primary_classification"] == "localized"


def test_error_attribution_does_not_overwrite_existing_output(tmp_path):
    from scripts.reproduce.analyze_original_error_attribution import analyze

    output = tmp_path / "attribution"
    output.mkdir()
    try:
        analyze(GT, RAW, EVALUATION, output)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing attribution output was overwritten")
