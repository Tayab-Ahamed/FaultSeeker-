"""Validate the bound cohort-manifest schema without changing evidence.

The repository has two admission representations: legacy flat records handled
by :mod:`benchmark.evidence_manifest`, and the bound-record manifests consumed
by :mod:`benchmark.research_protocol`.  This module is the explicit offline
gate for the latter.  It validates the published manifest's own accounting,
re-checks every bound artifact, and preserves a tri-state decision for
candidate records without treating missing evidence as a permanent exclusion.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from benchmark.evidence_manifest import CHAIN_IDS, HASH
from benchmark.research_protocol import admit, identity, read_bound


SUPPORTED_SCHEMAS = {2, 3}
TERMINAL_REASONS = {
    'DUPLICATE_CHAIN_TRANSACTION',
    'INVALID_IDENTITY_OR_CHAIN',
    'INVALID_BOUND_ARTIFACT',
    'MALFORMED_RECORD',
    'TRANSACTION_NOT_SUCCESSFUL',
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _infer_root(manifest_path: Path):
    for candidate in (manifest_path.parent, *manifest_path.parents):
        if (candidate / '.git').exists():
            return candidate
    return manifest_path.parents[1]


def _safe_identity(row):
    try:
        return identity(row)
    except (AttributeError, KeyError, TypeError):
        return ''


def _bound_artifacts(value, root: Path, seen=None):
    """Verify every nested ``{path, sha256}`` binding in a record."""
    seen = seen or set()
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            key = (value.get('path'), value.get('sha256'))
            if key in seen:
                return
            seen.add(key)
            if not isinstance(value['path'], str) or not isinstance(value['sha256'], str):
                raise ValueError('invalid bound artifact')
            read_bound(value, root)
        for child in value.values():
            _bound_artifacts(child, root, seen)
    elif isinstance(value, list):
        for child in value:
            _bound_artifacts(child, root, seen)


def _structural_reasons(record, root: Path):
    reasons = []
    if not isinstance(record, dict):
        return ['MALFORMED_RECORD']
    tx_hash = str(record.get('txn_hash', '')).lower()
    chain = record.get('chain')
    if not HASH.fullmatch(tx_hash) or chain not in CHAIN_IDS:
        reasons.append('INVALID_IDENTITY_OR_CHAIN')
    try:
        _bound_artifacts(record, root)
    except (KeyError, TypeError, ValueError, OSError):
        reasons.append('INVALID_BOUND_ARTIFACT')
    return reasons


def _status(reasons):
    reasons = set(reasons)
    if not reasons:
        return 'accepted'
    if reasons & TERMINAL_REASONS:
        return 'excluded'
    return 'pending'


def _decision(record, root: Path, duplicate=False):
    reasons = _structural_reasons(record, root)
    if duplicate:
        reasons.append('DUPLICATE_CHAIN_TRANSACTION')
    if not reasons:
        try:
            admission = admit(record, root)
            reasons.extend(admission.get('reasons', []))
        except (KeyError, TypeError, ValueError, OSError):
            reasons.append('MALFORMED_RECORD')
    tx_hash = str(record.get('txn_hash', '')).lower() if isinstance(record, dict) else ''
    chain = record.get('chain') if isinstance(record, dict) else None
    return {
        'txn_hash': tx_hash,
        'chain': chain,
        'status': _status(reasons),
        'accepted': not reasons,
        'reasons': sorted(set(reasons)),
    }


def audit_manifest(manifest_path, evidence_root=None, target=None):
    """Audit a published bound manifest and return a JSON-serializable report."""
    manifest_path = Path(manifest_path).resolve()
    root = Path(evidence_root).resolve() if evidence_root else _infer_root(manifest_path)
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError('cohort manifest must be an object')
    schema = manifest.get('schema')
    if schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f'unsupported cohort manifest schema: {schema!r}')
    records = manifest.get('records')
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError('cohort manifest records must be a list of objects')
    target = manifest.get('target_count', 246) if target is None else target
    if type(target) is not int or target < 1:
        raise ValueError('target_count must be a positive integer')

    ids = [_safe_identity(row) for row in records]
    counts = Counter(row.get('chain') for row in records)
    duplicate_ids = {item for item, count in Counter(ids).items() if item and count > 1}
    decisions = [_decision(row, root, _safe_identity(row) in duplicate_ids)
                 for row in records]
    accepted = sum(item['accepted'] for item in decisions)
    manifest_reasons = []
    if manifest.get('accepted_count') != len(records):
        manifest_reasons.append('MANIFEST_ACCEPTED_COUNT_MISMATCH')
    if manifest.get('remaining_to_target', max(0, target - len(records))) != max(0, target - len(records)):
        manifest_reasons.append('MANIFEST_REMAINING_COUNT_MISMATCH')
    declared_chains = manifest.get('chains')
    if declared_chains is not None and declared_chains != dict(sorted(counts.items())):
        manifest_reasons.append('MANIFEST_CHAIN_COUNTS_MISMATCH')
    if any(item['status'] != 'accepted' for item in decisions):
        manifest_reasons.append('PUBLISHED_RECORD_NOT_ACCEPTED')
    manifest_valid = not manifest_reasons
    return {
        'manifest_path': manifest_path.as_posix(),
        'evidence_root': root.as_posix(),
        'schema': schema,
        'manifest_valid': manifest_valid,
        'status': 'READY-FOR-EXPERIMENT' if manifest_valid and len(records) >= target else 'BLOCKED-BY-DATA',
        'target_count': target,
        'input_rows': len(records),
        'accepted_rows': accepted,
        'pending_rows': sum(item['status'] == 'pending' for item in decisions),
        'excluded_rows': sum(item['status'] == 'excluded' for item in decisions),
        'additional_verified_rows_needed': max(0, target - accepted),
        'declared_not_independent_human_review': manifest.get('not_independent_human_review'),
        'manifest_reasons': sorted(set(manifest_reasons)),
        'chain_counts': dict(sorted(counts.items())),
        'rows': decisions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--root', type=Path, help='Repository root containing bound artifact paths')
    parser.add_argument('--target', type=int, default=None)
    parser.add_argument('--strict', action='store_true',
                        help='Exit 2 unless the manifest is valid and reaches its target')
    args = parser.parse_args(argv)
    try:
        report = audit_manifest(args.manifest, args.root, args.target)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'INVALID-MANIFEST', 'error': str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report['status'] != 'READY-FOR-EXPERIMENT':
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
