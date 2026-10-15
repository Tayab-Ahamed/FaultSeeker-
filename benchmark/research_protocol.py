"""Evidence admission, train isolation and a durable one-use final-exam gate.

Cryptographic checks establish byte integrity, not that a publisher/reviewer is
truthful. Independence and mechanism review must be supplied as attributed
evidence; this module never manufactures labels from titles or receipt success.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import gzip
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re

from benchmark.evidence_manifest import CHAIN_IDS

HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode())


def _path(value, root):
    root = Path(root).resolve()
    path = (root / value).resolve()
    if (not path.is_relative_to(root) or '.git' in path.relative_to(root).parts
            or path.name.startswith('.env')):
        raise ValueError('Unsafe research artifact')
    return path


def bind(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return {'path': path.relative_to(root).as_posix(), 'sha256': sha(path.read_bytes())}


def read_bound(binding, root):
    path = _path(binding['path'], root)
    raw = path.read_bytes()
    if sha(raw) != binding['sha256']:
        raise ValueError('Research artifact digest mismatch')
    return raw


def source_text(raw):
    """Normalize visible text and source metadata without executing page code."""
    if raw.startswith(b'\x1f\x8b'):
        raw = gzip.decompress(raw)
    text = raw.decode('utf-8', errors='replace')
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)
        def handle_starttag(self, tag, attrs):
            self.parts.extend(v for k,v in attrs if v and k in ('content','alt','title','href','data-expanded-url'))
    parser = Text()
    parser.feed(text)
    return re.sub(r'\s+', ' ', unescape(' '.join(parser.parts)).replace('\\n',' ')).strip()


def identity(row):
    return row['chain'].lower() + ':' + row['txn_hash'].lower()


def admit(row, root):
    reasons = []
    txhash = str(row.get('txn_hash', '')).lower()
    chain = row.get('chain')
    if not HASH.fullmatch(txhash) or chain not in CHAIN_IDS:
        reasons.append('INVALID_IDENTITY_OR_CHAIN')
    rpc_ok = False
    try:
        rpc = json.loads(read_bound(row['rpc'], root))
        tx, receipt = rpc.get('transaction'), rpc.get('receipt')
        rpc_ok = bool(rpc.get('mode') == 'live-rpc' and rpc.get('chain_id') == CHAIN_IDS.get(chain)
            and rpc.get('txn_hash') == txhash and rpc.get('chain') == chain
            and isinstance(tx, dict) and isinstance(receipt, dict)
            and tx.get('hash', '').lower() == txhash and receipt.get('transactionHash', '').lower() == txhash
            and tx.get('blockHash') == receipt.get('blockHash') and HASH.fullmatch(str(tx.get('blockHash', '')))
            and int(str(tx.get('chainId')), 16) == CHAIN_IDS.get(chain))
        if not rpc_ok:
            reasons.append('RPC_IDENTITY_OR_RECEIPT_NOT_VERIFIED')
        elif receipt.get('status') != '0x1':
            reasons.append('TRANSACTION_NOT_SUCCESSFUL')
    except (KeyError, TypeError, ValueError, OSError):
        reasons.append('MISSING_OR_INVALID_RPC_EVIDENCE')
    publishers, bodies = set(), set()
    for source in row.get('sources', []):
        try:
            read_bound(source['artifact'], root)
            # Publisher aliases/mirrors share one independence group. Hash hits
            # alone cannot set the reviewed status.
            if (source.get('review_status') != 'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED'
                    or not source.get('independence_basis') or not source.get('identity_basis')
                    or not source.get('publisher_id') or not source.get('independence_group')):
                continue
            group = source['independence_group'].casefold()
            digest = source['artifact']['sha256']
            if digest not in bodies:
                publishers.add(group)
                bodies.add(digest)
        except (KeyError, TypeError, ValueError, OSError):
            continue
    if len(publishers) < 2:
        reasons.append('MISSING_TWO_INDEPENDENT_SECURITY_PUBLISHERS')
    annotation_ok = False
    try:
        annotation = json.loads(read_bound(row['annotation_record'], root))
        if (annotation.get('txn_hash') != txhash or annotation.get('chain') != chain
                or annotation.get('is_exploit') is not True or not annotation.get('vuln_type')
                or not annotation.get('adjudication_basis')
                or re.search(r'\b(TODO|TBD|NOT_ADJUDICATED|UNKNOWN)\b', annotation['vuln_type'], re.I)):
            raise ValueError('Incomplete adjudication')
        reviewer_ids = set()
        if annotation.get('mode') == 'public-source-consensus-v1':
            # Explicitly authorized public-source adjudication, not fictional
            # independent human reviewers. Both observations must come from
            # the same independently reviewed source artifacts as the row.
            if annotation.get('adjudication_author') != 'Codex':
                raise ValueError('Public adjudication author must be explicit')
            approved = {(s['publisher_id'],s['artifact']['sha256']):s for s in row.get('sources',[])
                        if s.get('review_status') == 'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED'}
            for observation in annotation.get('independent_observations',[]):
                key = (observation.get('publisher_id'),observation.get('source_artifact',{}).get('sha256'))
                if key not in approved or observation.get('vulnerability_class') != annotation['vuln_type']:
                    continue
                excerpt = re.sub(r'\s+',' ',observation.get('mechanism_excerpt','')).strip()
                if len(excerpt.split()) < 8:
                    continue
                text = source_text(read_bound(observation['source_artifact'],root))
                if excerpt.casefold() in text.casefold():
                    reviewer_ids.add(approved[key]['independence_group'].casefold())
        else:
            for bound in annotation.get('independent_reviews', []):
                review = json.loads(read_bound(bound, root))
                if (review.get('type') == 'independent-vulnerability-review'
                        and review.get('txn_hash') == txhash and review.get('chain') == chain
                        and review.get('reviewer_id') and review.get('qualification_evidence')
                        and review.get('mechanism_evidence') and review.get('independently_performed') is True
                        and review.get('vuln_type') == annotation['vuln_type']):
                    reviewer_ids.add(review['reviewer_id'].casefold())
        annotation_ok = len(reviewer_ids) >= 2 and type(annotation.get('uncategorized')) is bool
        if not annotation_ok:
            raise ValueError('Independent reviews absent')
    except (KeyError, TypeError, ValueError, OSError):
        reasons.append('MISSING_INDEPENDENT_ANNOTATION_EVIDENCE')
    return {'txn_hash': txhash, 'chain': chain, 'accepted': not reasons,
            'reasons': sorted(set(reasons)), 'rpc_identity_verified': rpc_ok,
            'independent_security_publishers': len(publishers), 'annotation_verified': annotation_ok,
            'scope': 'Evidence integrity plus attributed review records, not automated historical truth adjudication'}


def make_split(records, manifest_sha256, seed=1729):
    if type(seed) is not int or len(manifest_sha256) != 64:
        raise ValueError('Frozen input identity and integer seed required')
    records = sorted(records, key=identity)
    ids = [identity(r) for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate accepted transaction')
    result = {'schema': 1, 'manifest_sha256': manifest_sha256, 'seed': seed,
        'train_fraction': 0.7, 'heldout_fraction': 0.3,
        'stratification': ['chain', 'complexity_class'], 'grouping': 'incident_id, else transaction identity',
        'assignment': 'Seeded group order, minimizing per-stratum distance to 70% train targets; incident groups never split',
        'train_ids': [], 'heldout_ids': [], 'strata': []}
    if not records:
        return dict(result, status='BLOCKED_NO_ACCEPTED_DATA', reason='No accepted rows; partition not frozen')
    groups = defaultdict(list)
    strata = Counter((r['chain'], r.get('complexity_class', 'UNRECOVERED')) for r in records)
    for r in records:
        groups[r.get('incident_id') or identity(r)].append(r)
    if len(groups) < 2:
        return dict(result, status='BLOCKED_INSUFFICIENT_INDEPENDENT_INCIDENTS', reason='Cannot form independent partitions')
    train_counts = Counter()
    train, heldout = [], []
    for key in sorted(groups, key=lambda g: sha((str(seed)+':'+g).encode())):
        group = groups[key]
        weights = Counter((r['chain'], r.get('complexity_class', 'UNRECOVERED')) for r in group)
        before = sum(abs(train_counts[s] - .7*strata[s]) for s in weights)
        after = sum(abs(train_counts[s] + w - .7*strata[s]) for s, w in weights.items())
        global_before = abs(len(train) - .7*len(records))
        global_after = abs(len(train) + len(group) - .7*len(records))
        if after < before or (after == before and global_after < global_before):
            train.extend(group)
            train_counts.update(weights)
        else:
            heldout.extend(group)
    if not heldout or not train:
        return dict(result, status='BLOCKED_INSUFFICIENT_STRATIFIABLE_DATA', reason='Rounding/group constraints leave an empty partition')
    result.update(status='FROZEN', train_ids=sorted(map(identity, train)), heldout_ids=sorted(map(identity, heldout)))
    for s, count in sorted(strata.items()):
        result['strata'].append({'chain':s[0], 'complexity_class':s[1], 'total':count,
                                'train':train_counts[s], 'heldout':count-train_counts[s],
                                'rounding_deviation':train_counts[s]-.7*count})
    return result


def load_train(split, root):
    if split.get('status') != 'FROZEN':
        raise ValueError('No frozen train partition')
    rows = json.loads(read_bound(split['partitions']['train'], root))
    if sorted(map(identity, rows)) != sorted(split['train_ids']):
        raise ValueError('Train membership mismatch')
    return rows


def claim_exam(path, split, system_sha256):
    if split.get('status') != 'FROZEN' or not split.get('train_ids') or not split.get('heldout_ids'):
        raise ValueError('Final exam requires nonempty frozen partitions')
    if not re.fullmatch('[a-f0-9]{64}', system_sha256):
        raise ValueError('Frozen system identity required')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is the concurrency boundary. A dispatched/failed exam
    # remains consumed; callers cannot truncate this file or silently retry.
    with path.open('x', encoding='utf-8') as handle:
        json.dump({'status':'CONSUMED_BEFORE_HELDOUT_LOAD', 'system_sha256':system_sha256,
                   'split_sha256':sha(canonical(split)), 'created_at':datetime.now(timezone.utc).isoformat()}, handle)
        handle.flush()
        os.fsync(handle.fileno())


def append_experiment(path, split, event):
    event = dict(event)
    samples = event.get('sample_ids', [])
    if event.get('kind') == 'scored-train':
        if not samples:
            raise ValueError('Cannot score an empty train population')
        if split.get('status') != 'FROZEN' or not set(samples) <= set(split['train_ids']):
            raise ValueError('Only train membership may be evaluated for optimization')
    elif event.get('metrics') is not None:
        raise ValueError('Unscored/preflight events cannot contain invented metrics')
    if 'config' not in event or type(event.get('seed')) is not int:
        raise ValueError('Every experiment needs a config and seed')
    path = Path(path)
    previous = json.loads(path.read_text()) if path.exists() else []
    if not isinstance(previous, list):
        raise ValueError('Corrupt experiment log; refusing to reset')
    event.update(sequence=len(previous)+1, previous_sha256=sha(canonical(previous)),
                 timestamp=datetime.now(timezone.utc).isoformat())
    write_json(path, previous + [event])
