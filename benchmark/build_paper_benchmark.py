"""Freeze an evidence-complete cohort; never repair or pad missing incidents."""
import csv
import json
from pathlib import Path
from benchmark.evidence_manifest import audit_dataset


def freeze_cohort(source, output, evidence_root=None, target=246):
    source, output = Path(source), Path(output)
    audit = audit_dataset(source, evidence_root=evidence_root, target=target)
    if audit['accepted_rows'] != target or audit['input_rows'] != target:
        raise ValueError(f"BLOCKED-BY-DATA: require exactly {target} unique accepted rows; "
                         f"have {audit['accepted_rows']} accepted of {audit['input_rows']}")
    if source.suffix.lower() == '.json':
        records = json.loads(source.read_text(encoding='utf-8-sig'))
        records = records['records'] if isinstance(records, dict) else records
    else:
        with source.open(encoding='utf-8-sig', newline='') as handle:
            records = list(csv.DictReader(handle))
    payload = {'schema': 'faultseeker-evidence-cohort-v1',
               'source_sha256': audit['dataset_sha256'], 'records': records,
               'verification_scope': 'artifact-integrity; canonical confirmations recorded in per-row artifacts'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload
