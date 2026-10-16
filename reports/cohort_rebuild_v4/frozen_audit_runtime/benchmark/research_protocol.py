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


def transaction_chain_id(tx):
    """Recover omitted legacy chainId using EIP-155, never endpoint assumptions."""
    def integer(value):
        if isinstance(value, bool):
            raise ValueError('Invalid integer')
        return value if isinstance(value, int) else int(value, 16)
    declared = integer(tx['chainId']) if tx.get('chainId') is not None else None
    inferred = None
    if integer(tx.get('type', '0x0')) == 0 and tx.get('v') is not None:
        v = integer(tx['v'])
        if v >= 35:
            inferred = (v-35)//2
    if declared is not None and inferred is not None and declared != inferred:
        raise ValueError('Signature and declared chain ID disagree')
    chain = declared if declared is not None else inferred
    if chain is None or chain <= 0:
        raise ValueError('Transaction has no verifiable chain ID')
    return chain


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
            and transaction_chain_id(tx) == CHAIN_IDS.get(chain))
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
        'assignment': 'Seeded group order minimizes stratum distance, then whole-group moves improve global 70/30 rounding with minimum stratum penalty; incident groups never split',
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
    # Sparse singleton strata otherwise all enter train. Improve global rounding
    # using identities and strata only, never labels or model predictions.
    while True:
        current_distance = abs(len(train)-.7*len(records))
        moves = []
        train_id_set = set(map(identity, train))
        for key, group in groups.items():
            in_train = identity(group[0]) in train_id_set
            delta = -len(group) if in_train else len(group)
            next_size = len(train)+delta
            distance = abs(next_size-.7*len(records))
            if not 0 < next_size < len(records) or distance >= current_distance:
                continue
            weights = Counter((r['chain'],r.get('complexity_class','UNRECOVERED')) for r in group)
            sign = -1 if in_train else 1
            penalty = sum(abs(train_counts[s]+sign*w-.7*strata[s])
                          - abs(train_counts[s]-.7*strata[s]) for s,w in weights.items())
            moves.append((distance,penalty,sha((str(seed)+':'+key).encode()),key,in_train))
        if not moves:
            break
        _,_,_,key,in_train = min(moves)
        group = groups[key]
        group_ids = set(map(identity,group))
        if in_train:
            train = [r for r in train if identity(r) not in group_ids]
            heldout.extend(group)
        else:
            heldout = [r for r in heldout if identity(r) not in group_ids]
            train.extend(group)
        train_counts = Counter((r['chain'],r.get('complexity_class','UNRECOVERED')) for r in train)
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


def load_train_split(root, split_file=None):
    """Validate the selected freeze without opening its held-out partition."""
    root = Path(root).resolve()
    if split_file is not None and not str(split_file):
        raise ValueError('Explicit train split path is empty')
    split_path = (root / ('benchmark/eval_split.json' if split_file is None else split_file)).resolve()
    if (not split_path.is_relative_to(root) or '.git' in split_path.relative_to(root).parts
            or split_path.name.startswith('.env')):
        raise ValueError('Unsafe train split path')
    split = json.loads(split_path.read_text())
    manifest = split.get('manifest')
    if manifest is None:
        if split_file is not None:
            raise ValueError('Selected split requires a bound manifest')
        raw = (root / 'benchmark/cohort_manifest.json').read_bytes()
    else:
        raw = read_bound(manifest, root)
    if sha(raw) != split['manifest_sha256']:
        raise ValueError('Frozen manifest digest mismatch')
    train_ids, heldout_ids = split['train_ids'], split.get('heldout_ids', [])
    if set(train_ids) & set(heldout_ids):
        raise ValueError('Train and held-out memberships overlap')
    if split_file is not None:
        records = json.loads(raw)['records']
        manifest_ids = [identity(row) for row in records]
        if (len(set(manifest_ids)) != len(manifest_ids)
                or len(set(train_ids)) != len(train_ids)
                or len(set(heldout_ids)) != len(heldout_ids)
                or set(manifest_ids) != set(train_ids) | set(heldout_ids)):
            raise ValueError('Selected manifest and split membership mismatch or duplicate')
        # Manifest records are public provenance. Only the TRAIN partition body
        # is opened; its full records must match the pinned public manifest.
        by_identity = {identity(row): row for row in records}
        for row in load_train(split, root):
            if row != by_identity[identity(row)]:
                raise ValueError('Selected train record differs from pinned manifest')
    return split_path, split



def acquisition_directory(root, split_file):
    """An explicit split gets an isolated namespace keyed by its exact bytes."""
    root = Path(root).resolve()
    split_path, _ = load_train_split(root, split_file)
    return root / 'reports/cohort_rebuild_v2/acquisitions' / sha(split_path.read_bytes())


def load_acquisition_indexes(root, split_file=None):
    """Merge selected TRAIN metadata; excluded capture bodies are never read.

    Version indexes point at immutable snapshots. Existing legacy index bytes
    and their artifact bindings remain untouched and usable by the old freeze.
    """
    root = Path(root).resolve()
    split_path, split = load_train_split(root, split_file)
    split_binding = bind(split_path, root)
    legacy = root / 'reports/cohort_rebuild_v2'
    version = acquisition_directory(root, split_file) if split_file is not None else None
    merged, bindings = {}, []
    for kind in ('opcode', 'trace'):
        merged[kind] = {}
        paths = [legacy / (kind + '_acquisition_train.json')]
        if version is not None:
            paths.append(version / (kind + '_acquisition_train.json'))
        for path in paths:
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            index_binding = bind(path, root)
            if version is not None and path.parent == version:
                if data.get('split') != split_binding or 'snapshot' not in data:
                    raise ValueError('Version acquisition index is not bound to selected split')
                index_binding = data['snapshot']
                data = json.loads(read_bound(index_binding, root))
                if data.get('split') != split_binding:
                    raise ValueError('Acquisition snapshot split mismatch')
            records = data.get('attempts', []) if isinstance(data, dict) else data
            keys = [r['identity'] for r in records]
            if len(set(keys)) != len(keys):
                raise ValueError('Duplicate identity in acquisition index')
            if split_file is None and not set(keys) <= set(split['train_ids']):
                raise ValueError('Non-train identity in acquisition index')
            if version is not None and path.parent == version and not set(keys) <= set(split['train_ids']):
                raise ValueError('Version acquisition index contains non-train identities')
            for record in records:
                if record['identity'] in split['train_ids']:
                    # A failed version attempt must not erase usable legacy
                    # evidence. Captured artifact integrity is checked on load.
                    key = record['identity']
                    if key not in merged[kind] or record.get('artifact'):
                        merged[kind][key] = record
            bindings.append(index_binding)
    return merged, bindings


def acquisition_records(root, admitted_path, split_file=None):
    """After freezing, acquisition may open only the bound train population."""
    root=Path(root).resolve()
    if split_file is not None:
        _, split = load_train_split(root, split_file)
        return load_train(split, root)
    split_path=root/'benchmark/eval_split.json'
    if split_path.exists():
        return load_train(json.loads(split_path.read_text()),root)
    path=Path(admitted_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Admission path escapes workspace')
    return json.loads(path.read_text())


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
