"""Offline historical admission reproduction using a hash-pinned own Git evaluator.

This replays the original 21-record population snapshot; it does not describe
current cohort availability or execute code embedded in the original report.
"""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

PINS = {'original_audit': {'path': 'reports/cohort_rebuild_v4/FROZEN_231_REAUDIT.json', 'sha256': '7b68d56b11de97708cebc3fa3494441251150e8f7d442556394b1485d2bd386d'}, 'archived_package': [{'path': 'reports/cohort_rebuild_v4/frozen_audit_runtime/benchmark/research_protocol.py', 'sha256': '0c1c267132726f70dd843a275854f038caaded89c9705f69a828818e518746ab'}, {'path': 'reports/cohort_rebuild_v4/frozen_audit_runtime/benchmark/evidence_manifest.py', 'sha256': '2eacb9bd04df52b065da7ac83e8ad0c9bd1653796d39b4470dc6a7aef9e50274'}, {'path': 'reports/cohort_rebuild_v4/frozen_audit_runtime/benchmark/__init__.py', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}]}
ROOT = Path(__file__).resolve().parents[3]

def checked(binding):
    path = (ROOT / binding['path']).resolve()
    if (not path.is_relative_to(ROOT) or '.git' in path.relative_to(ROOT).parts
            or path.name.startswith('.env')):
        raise ValueError('Unsafe historical reproduction artifact')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('Historical reproduction digest mismatch')
    return raw

# Check archived Python bytes before importing the trusted Git snapshot.
for source in PINS['archived_package']:
    checked(source)
from benchmark import research_protocol as evaluator
assert Path(evaluator.__file__).resolve() == Path(__file__).resolve().parent / 'benchmark/research_protocol.py'
assert next(x['sha256'] for x in PINS['archived_package'] if x['path'].endswith('/research_protocol.py')) == json.loads(checked(PINS['original_audit']))['evaluator']['sha256']
audit = json.loads(evaluator.read_bound(PINS['original_audit'], ROOT))
frozen = list(csv.DictReader(io.StringIO(evaluator.read_bound(audit['frozen_csv'], ROOT).decode('utf-8-sig'))))
assert len(frozen) == audit['input_rows'] == 231
assert len(set(map(evaluator.identity, frozen))) == audit['unique_identities'] == 231
assert [evaluator.identity(row) for row in frozen] == [row['identity'] for row in audit['rows']]
assert [row['frozen_row_number'] for row in audit['rows']] == list(range(1, 232))
assert [evaluator.identity(row['effective_evidence_record']) for row in audit['rows']] == [row['identity'] for row in audit['rows']]
observed = [evaluator.admit(row['effective_evidence_record'], ROOT) for row in audit['rows']]
assert observed == [row['decision'] for row in audit['rows']]
accepted = sum(row['accepted'] for row in observed)
quarantined = len(observed) - accepted
reasons = dict(Counter(reason for row in observed for reason in row['reasons']))
assert accepted == audit['accepted_count'] == 6
assert quarantined == audit['quarantined_count'] == 225
assert reasons == audit['missing_reason_counts']
assert [evaluator.identity(row) for row in observed if row['accepted']] == audit['accepted_identities']
assert audit['available_authentic_population'] == 21
print(json.dumps({'input_rows': len(observed), 'accepted_count': accepted,
    'quarantined_count': quarantined, 'missing_reason_counts': reasons,
    'all_original_decisions_match': True,
    'historical_available_authentic_population_snapshot': audit['available_authentic_population'],
    'scope': 'Historical 21-record population snapshot; no claim about current population',
    'model_requests': 0, 'network_requests': 0,
    'heldout_partition_payload_opened': False}, sort_keys=True))
