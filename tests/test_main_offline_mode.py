"""Focused coverage for the opt-in no-LLM entry-point mode."""

import builtins
import json

from faultseeker import main as entrypoint


def test_offline_mode_skips_model_selection_and_pipeline(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("faultseeker.core.auto_model_selector") or name.startswith("faultseeker.core.pipeline"):
            raise AssertionError("offline mode must not import model/pipeline setup")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    output = tmp_path / "offline.json"
    result = entrypoint.main(
        txn_hash="0x" + "a" * 64,
        chain="eth",
        cache_dir=str(tmp_path / "cache"),
        output_path=str(output),
        offline=True,
    )

    assert result["analysis_mode"] == "offline-no-llm"
    assert result["stage_completed"] == "stage1"
    assert result["stage2_bypassed"] is True
    assert result["llm_cost"] == 0.0
    assert result["query_records"] == []
    assert json.loads(output.read_text())["analysis_mode"] == "offline-no-llm"
