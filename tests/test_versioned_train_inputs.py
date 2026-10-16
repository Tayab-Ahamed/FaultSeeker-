"""Software-only version-selection tests; never empirical claim evidence."""
import json
from pathlib import Path

import pytest

from benchmark.research_protocol import bind, identity, sha, write_json
from tests.test_authentic_research_runner import training_workspace
from tests.test_authentic_publication import fixture_record


def versioned_workspace(root):
    original = training_workspace(root)
    added = fixture_record(root, 2)
    added['reentrancy_label'] = False
    version = root / 'benchmark/versions/test-version'
    write_json(version / 'cohort_manifest.json', {'accepted_count': 2, 'version': 'test-version', 'records': [original, added]})
    write_json(version / 'train.json', [added])
    manifest = bind(version / 'cohort_manifest.json', root)
    split = {'status': 'FROZEN', 'seed': 1729, 'train_ids': [identity(added)],
             'heldout_ids': [identity(original)], 'manifest': manifest,
             'manifest_sha256': manifest['sha256'],
             'partitions': {'train': bind(version / 'train.json', root),
                            'heldout': {'path': 'NEVER_OPEN_HELDOUT.json', 'sha256': '0' * 64}}}
    path = version / 'eval_split.json'
    write_json(path, split)
    return original, added, path


def guard_heldout_reads(monkeypatch):
    read_bytes, read_text = Path.read_bytes, Path.read_text
    def guarded_bytes(path, *args, **kwargs):
        assert 'HELDOUT' not in path.name.upper(), 'TRAIN command opened held-out partition'
        return read_bytes(path, *args, **kwargs)
    def guarded_text(path, *args, **kwargs):
        assert 'HELDOUT' not in path.name.upper(), 'TRAIN command opened held-out partition'
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_bytes', guarded_bytes)
    monkeypatch.setattr(Path, 'read_text', guarded_text)


def test_selected_capture_loader_rejects_old_train_before_capture_loading(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    original, _, split = versioned_workspace(tmp_path)
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='outside frozen train'):
        load_train_inputs(tmp_path, identity(original), split_file=split)


def test_selected_new_train_missing_capture_is_missing_not_legacy_fallback(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    _, added, split = versioned_workspace(tmp_path)
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='No recorded trace'):
        load_train_inputs(tmp_path, identity(added), split_file=split)


def test_selected_manifest_is_bound_and_never_falls_back(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    _, added, split = versioned_workspace(tmp_path)
    (split.parent / 'cohort_manifest.json').write_bytes(b'changed')
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='digest'):
        load_train_inputs(tmp_path, identity(added), split_file=split)


@pytest.mark.parametrize('module_name', ['run_authentic_research', 'run_train_production'])
def test_local_runner_uses_selected_allowlist_and_records_split(tmp_path, monkeypatch, module_name):
    import importlib
    runner = importlib.import_module('scripts.' + module_name)
    original, added, split = versioned_workspace(tmp_path)
    # Old acquisition entries may exist, but their captured data must never enter
    # a version where that identity belongs to the held-out partition.
    write_json(tmp_path / 'reports/cohort_rebuild_v2/trace_acquisition_train.json',
               [{'identity': identity(original), 'artifact': {'path': 'NEVER_OPEN_HELDOUT_TRACE.json', 'sha256': '0' * 64}}])
    guard_heldout_reads(monkeypatch)
    result = runner.run_train(tmp_path, split_file=split.relative_to(tmp_path))
    assert result['config']['split'] == bind(split, tmp_path)
    assert result['config']['manifest'] == bind(split.parent / 'cohort_manifest.json', tmp_path)
    if module_name == 'run_authentic_research':
        for variant in result['variants'].values():
            assert variant['metrics'] is None
            assert variant['missing'][0]['identity'] == identity(added)
    else:
        assert result['coverage'] == {'observed': 0, 'requested_train': 1}
        assert result['missing'][0]['identity'] == identity(added)
    events = json.loads((tmp_path / 'reports/cohort_rebuild_v2/experiments_log.json').read_text())
    assert all(event['config']['split'] == bind(split, tmp_path) for event in events)
    assert all(set(event['sample_ids']) <= {identity(added)} for event in events)


def test_production_runner_propagates_split_to_observation(tmp_path, monkeypatch):
    from scripts import run_train_production as runner
    _, added, split = versioned_workspace(tmp_path)
    observed = []
    def observe(root, key, cache_dir, split_file=None):
        observed.append((key, Path(split_file)))
        raise ValueError('No captured input for this software test')
    monkeypatch.setattr(runner, 'observe_stage_one', observe)
    guard_heldout_reads(monkeypatch)
    runner.run_train(tmp_path, split_file=split)
    assert observed == [(identity(added), split)]


@pytest.mark.parametrize('module_name', ['run_authentic_research', 'run_train_production'])
def test_cli_propagates_explicit_split(monkeypatch, module_name):
    import importlib
    runner = importlib.import_module('scripts.' + module_name)
    calls = []
    monkeypatch.setattr(runner, 'run_train', lambda **kwargs: calls.append(kwargs))
    runner.main(['--split-file', 'benchmark/versions/test-version/eval_split.json'])
    assert calls[0]['split_file'] == 'benchmark/versions/test-version/eval_split.json'


def test_selected_train_can_reuse_its_own_hash_bound_capture(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    original, added, split_path = versioned_workspace(tmp_path)
    split = json.loads(split_path.read_text())
    write_json(split_path.parent / 'train.json', [original])
    split['train_ids'], split['heldout_ids'] = [identity(original)], [identity(added)]
    split['partitions']['train'] = bind(split_path.parent / 'train.json', tmp_path)
    write_json(split_path, split)
    guard_heldout_reads(monkeypatch)
    inputs = load_train_inputs(tmp_path, identity(original), require_opcodes=False, split_file=split_path)
    assert inputs.structured['transaction_hash'] == original['txn_hash']
    assert inputs.evidence['capture'] == original['trace']
    assert 'reentrancy_label' not in inputs.structured


@pytest.mark.parametrize('problem', ['missing-binding', 'manifest-disagrees', 'overlap', 'train-membership'])
def test_selected_split_rejects_invalid_binding_or_membership(tmp_path, monkeypatch, problem):
    from benchmark.captured_inputs import load_train_inputs
    original, added, split_path = versioned_workspace(tmp_path)
    split = json.loads(split_path.read_text())
    if problem == 'missing-binding':
        del split['manifest']
    elif problem == 'manifest-disagrees':
        split['manifest_sha256'] = '0' * 64
    elif problem == 'overlap':
        split['heldout_ids'] = split['train_ids']
    else:
        write_json(split_path.parent / 'train.json', [original])
        split['partitions']['train'] = bind(split_path.parent / 'train.json', tmp_path)
    write_json(split_path, split)
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError):
        load_train_inputs(tmp_path, identity(added), split_file=split_path)


def test_explicit_empty_split_never_defaults_to_legacy(tmp_path):
    from benchmark.captured_inputs import load_train_inputs
    original, _, _ = versioned_workspace(tmp_path)
    with pytest.raises(ValueError, match='empty'):
        load_train_inputs(tmp_path, identity(original), require_opcodes=False, split_file='')


@pytest.mark.parametrize('change', ['extra-identity', 'changed-label'])
def test_explicit_train_must_match_pinned_manifest_records(tmp_path, monkeypatch, change):
    from benchmark.captured_inputs import load_train_inputs
    _, added, split_path = versioned_workspace(tmp_path)
    split = json.loads(split_path.read_text())
    rows = [added]
    if change == 'extra-identity':
        extra = fixture_record(tmp_path, 3)
        extra['reentrancy_label'] = True
        rows.append(extra)
        split['train_ids'].append(identity(extra))
    else:
        rows[0]['reentrancy_label'] = True
    write_json(split_path.parent / 'train.json', rows)
    split['partitions']['train'] = bind(split_path.parent / 'train.json', tmp_path)
    write_json(split_path, split)
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='manifest'):
        load_train_inputs(tmp_path, identity(added), require_opcodes=False, split_file=split_path)


def test_explicit_manifest_duplicate_identities_rejected(tmp_path, monkeypatch):
    from benchmark.captured_inputs import load_train_inputs
    _, added, split_path = versioned_workspace(tmp_path)
    split = json.loads(split_path.read_text())
    path = split_path.parent / 'cohort_manifest.json'
    manifest = json.loads(path.read_text())
    manifest['records'].append(added)
    write_json(path, manifest)
    split['manifest'] = bind(path, tmp_path)
    split['manifest_sha256'] = split['manifest']['sha256']
    write_json(split_path, split)
    guard_heldout_reads(monkeypatch)
    with pytest.raises(ValueError, match='manifest'):
        load_train_inputs(tmp_path, identity(added), require_opcodes=False, split_file=split_path)
