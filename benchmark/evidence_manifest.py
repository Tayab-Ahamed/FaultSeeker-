"""Inspect every cohort record without trusting legacy 'verified' labels.

Acceptance requires acquisition artifacts and independent adjudication. This is
an artifact integrity gate, not an independent proof of canonical chain history:
live collection/replay must produce the verification record before publication.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

CHAIN_IDS = {'eth': 1, 'bsc': 56, 'polygon': 137, 'arbitrum': 42161,
             'optimism': 10, 'avalanche': 43114, 'base': 8453,
             'fantom': 250, 'gnosis': 100, 'zksync': 324}
HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact(root, value):
    if not isinstance(value, str) or not value:
        return None
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError('artifact escapes evidence root')
    return path


def _json_artifact(record, key, root, missing):
    value = record.get(key)
    if not value:
        missing.append('missing_' + key)
        return None, None
    try:
        path = _artifact(root, value)
    except ValueError:
        missing.append('unsafe_' + key + '_path')
        return None, None
    if not path or not path.is_file():
        missing.append('missing_' + key)
        return None, None
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        missing.append('invalid_' + key + '_json')
        return None, path
    if not isinstance(data, dict):
        missing.append('invalid_' + key + '_object')
        return None, path
    return data, path


def _hex_int(value):
    try:
        return int(value, 16) if isinstance(value, str) and value.startswith('0x') else int(value)
    except (TypeError, ValueError):
        return None


def validate_record(record, evidence_root):
    root = Path(evidence_root).resolve()
    missing = []
    txn_hash = str(record.get('txn_hash') or '').lower()
    chain = str(record.get('chain') or '').lower()
    if not HASH.fullmatch(txn_hash):
        missing.append('invalid_transaction_hash')
    if chain not in CHAIN_IDS:
        missing.append('unsupported_chain')
    tx, tx_path = _json_artifact(record, 'transaction', root, missing)
    receipt, receipt_path = _json_artifact(record, 'receipt', root, missing)
    trace, trace_path = _json_artifact(record, 'trace', root, missing)
    gt, _ = _json_artifact(record, 'ground_truth', root, missing)
    verification, _ = _json_artifact(record, 'verification', root, missing)
    if tx:
        if str(tx.get('hash', '')).lower() != txn_hash:
            missing.append('transaction_identity_mismatch')
        if _hex_int(tx.get('chainId')) != CHAIN_IDS.get(chain):
            missing.append('transaction_chain_mismatch')
    if receipt:
        if str(receipt.get('transactionHash', '')).lower() != txn_hash:
            missing.append('receipt_identity_mismatch')
        if not HASH.fullmatch(str(receipt.get('blockHash') or '')):
            missing.append('missing_block_identity')
        if _hex_int(receipt.get('blockNumber')) is None:
            missing.append('missing_block_number')
        if tx and tx.get('blockHash') != receipt.get('blockHash'):
            missing.append('transaction_receipt_block_mismatch')
    if trace:
        if str(trace.get('transaction_hash', '')).lower() != txn_hash or trace.get('chain') != chain:
            missing.append('trace_identity_mismatch')
        if not trace.get('raw_trace'):
            missing.append('missing_raw_trace')
        if trace.get('complete') is not True:
            missing.append('incomplete_trace')
        if not trace.get('tracer_config') or not trace.get('capture_version'):
            missing.append('missing_trace_configuration')
    if gt:
        hashes = gt.get('transaction_hash', [])
        hashes = [hashes] if isinstance(hashes, str) else hashes
        if not isinstance(hashes, list) or txn_hash not in [str(h).lower() for h in hashes]:
            missing.append('ground_truth_identity_mismatch')
        if (not gt.get('location') and gt.get('is_exploit') is not False) or not gt.get('cause'):
            missing.append('missing_ground_truth_label_or_location')
    sources = record.get('sources', [])
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except ValueError:
            sources = []
    publishers = set()
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            continue
        url = urlparse(str(source.get('url') or ''))
        publisher = source.get('publisher_id')
        try:
            path = _artifact(root, source.get('artifact'))
            valid = path and path.is_file() and digest_file(path) == source.get('sha256')
        except (ValueError, OSError):
            valid = False
        if isinstance(publisher,str) and publisher.strip() and url.scheme == 'https' and url.hostname and valid:
            publishers.add(publisher)
    if len(publishers) < 2:
        missing.append('missing_independent_sources')
    annotation = record.get('annotation', {})
    if isinstance(annotation, str):
        try:
            annotation = json.loads(annotation)
        except ValueError:
            annotation = {}
    reviewers = annotation.get('reviewers', []) if isinstance(annotation,dict) else []
    valid_reviewers = (isinstance(reviewers,list) and all(isinstance(item,str) and item.strip() for item in reviewers))
    if not valid_reviewers or len({item.strip().casefold() for item in reviewers}) < 2:
        missing.append('missing_independent_annotation')
    elif (not annotation.get('adjudicated_label') or
          (not annotation.get('attacker_addresses') and not (gt and gt.get('is_exploit') is False))):
        missing.append('missing_adjudicated_label_or_attacker')
    if (gt and gt.get('is_exploit') is False and isinstance(annotation,dict)
            and str(annotation.get('adjudicated_label','')).strip().lower() != 'benign'):
        missing.append('benign_ground_truth_annotation_mismatch')
    if verification:
        if verification.get('mode') != 'live-rpc-and-replay':
            missing.append('unverified_acquisition_mode')
        if verification.get('chain_id') != CHAIN_IDS.get(chain):
            missing.append('verification_chain_mismatch')
        endpoints = verification.get('rpc_endpoints', [])
        if (not isinstance(endpoints,list) or any(not isinstance(item,str) or not item.strip() for item in endpoints)
                or len({item.strip().casefold() for item in endpoints}) < 2):
            missing.append('missing_independent_rpc_confirmation')
        for key, path in [('transaction', tx_path), ('receipt', receipt_path), ('trace', trace_path)]:
            if path and path.is_file() and verification.get(key + '_sha256') != digest_file(path):
                missing.append(key + '_digest_mismatch')
        if receipt and verification.get('canonical_block_hash') != receipt.get('blockHash'):
            missing.append('canonical_block_mismatch')
        if not verification.get('verified_at') or not verification.get('tool_versions'):
            missing.append('missing_verification_environment')
    return {'txn_hash': txn_hash, 'chain': chain, 'accepted': not missing,
            'missing': sorted(set(missing)), 'verification_scope': 'artifact-integrity'}


def audit_dataset(path, evidence_root=None, target=246):
    path = Path(path)
    if target < 1:
        raise ValueError('target must be positive')
    if path.suffix.lower() == '.json':
        records = json.loads(path.read_text(encoding='utf-8-sig'))
        records = records.get('records', []) if isinstance(records, dict) else records
    else:
        with path.open(encoding='utf-8-sig', newline='') as f:
            records = list(csv.DictReader(f))
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise ValueError('dataset must contain a list of record objects')
    results, seen = [], set()
    for index, record in enumerate(records, 2):
        row = validate_record(record, evidence_root or path.parent)
        row['input_line'] = index
        identity = (row['chain'], row['txn_hash'])
        if identity in seen:
            row['missing'].append('duplicate_chain_transaction')
            row['accepted'] = False
        seen.add(identity)
        for field in ('functioncall_count', 'address_count', 'max_depth', 'gas_cost'):
            value = record.get(field)
            if value not in (None, ''):
                try:
                    number = float(value)
                    if not math.isfinite(number) or number < 0:
                        raise ValueError()
                except (TypeError, ValueError):
                    row['missing'].append('invalid_numeric_' + field)
                    row['accepted'] = False
        results.append(row)
    accepted = sum(r['accepted'] for r in results)
    return {'status': 'READY-FOR-EXPERIMENT' if accepted >= target else 'BLOCKED-BY-DATA',
            'dataset_sha256': digest_file(path), 'input_rows': len(records),
            'accepted_rows': accepted, 'target_rows': target,
            'additional_verified_rows_needed': max(0, target - accepted),
            'missing_counts': dict(Counter(reason for r in results for reason in r['missing'])),
            'rows': results}
