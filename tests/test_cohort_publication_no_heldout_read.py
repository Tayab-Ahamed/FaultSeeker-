"""Software-only publication isolation regressions, never research evidence."""
import json
from pathlib import Path
from benchmark.cohort_versions import publish_extension
from benchmark.research_protocol import sha
from tests.test_cohort_versions import fixture_publication


def test_publication_hashes_written_bytes_without_reopening_heldout(tmp_path, monkeypatch):
    parent, additions = fixture_publication(tmp_path, monkeypatch)
    original_open = Path.open
    def guard(path, mode="r", *args, **kwargs):
        if path.name == "heldout.json" and not any(flag in mode for flag in ("w", "a", "x")):
            raise AssertionError("Publication must not reopen held-out payload")
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guard)
    result = publish_extension(tmp_path, "versions/v2", parent, additions, {})
    split = json.loads((tmp_path / result["split"]["path"]).read_text())
    monkeypatch.setattr(Path, "open", original_open)
    binding = split["partitions"]["heldout"]
    assert binding["sha256"] == sha((tmp_path / binding["path"]).read_bytes())
