from scripts.research.reconcile_original_benchmarks import _row_overlap


def test_reconciliation_preserves_denominators_and_duplicate_identity():
    rows, summary = _row_overlap()

    assert summary["root_classification_rows"] == 115
    assert summary["original_classification_rows"] == 115
    assert summary["classification_rows_equal"] is True
    assert summary["original_ground_truth_files"] == 115
    assert summary["original_ground_truth_unique_stable_ids"] == 114
    assert summary["current_114_localization_denominator"] == 114
    assert summary["faultseekerpp_target_count"] == 246
    assert summary["faultseekerpp_accepted_manifest_rows"] == 14
    assert summary["faultseekerpp_remaining_to_target"] == 232
    assert summary["original_faultseekerpp_transaction_overlap"] == 4
    assert summary["faultseekerpp_v4_manifest"]["accepted_count"] == 22
    assert summary["faultseekerpp_v4_manifest"]["target_count"] == 246
    assert summary["faultseekerpp_v4_manifest"]["remaining_to_target"] == 224
    assert summary["faultseekerpp_v4_manifest"]["not_independent_human_review"] is True

    duplicate = next(row for row in rows if row["original_gt_duplicate_file_count"] == 2)
    assert duplicate["stable_id"].startswith("eth:0x6439d63c")
    assert len(duplicate["original_gt_source_files"]) == 2
