"""Rebuild every available cohort row without inventing provenance or labels."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evidence_manifest import audit_dataset, digest_file


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2)+'\n').encode())


def inventory_ground_truth(directory):
    rows = []
    for path in sorted(Path(directory).glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            hashes = data.get('transaction_hash',[])
            if isinstance(hashes,str):
                hashes = [hashes]
            valid_hashes = [str(h).lower() for h in hashes] if isinstance(hashes,list) else []
            rows.append({'file':path.name,'sha256':digest_file(path),'payload_hashes':valid_hashes,
                'filename_identity_matches_payload':path.stem.lower() in valid_hashes,
                'name':data.get('name'),'cause':data.get('cause'),'readable':True})
        except (ValueError,OSError,AttributeError):
            rows.append({'file':path.name,'sha256':digest_file(path),'readable':False,
                         'filename_identity_matches_payload':False,'payload_hashes':[]})
    return rows


def rebuild(source, gt_directory, output, captures=(), source_artifacts=()):
    source, gt_directory, output = Path(source), Path(gt_directory), Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with source.open(encoding='utf-8-sig') as handle:
        original = list(csv.DictReader(handle))
    inventory = inventory_ground_truth(gt_directory)
    by_filename = {row['file']:row for row in inventory}
    captured = {}
    for path in captures:
        with gzip.open(path,'rt',encoding='utf-8') as handle:
            capture = json.load(handle)
        from scripts.replay_historical_opcodes import validate_recorded_capture
        proof = validate_recorded_capture(path,capture['transaction_hash'])
        captured[capture['transaction_hash'].lower()] = (capture,proof,str(path))
    rebuilt, supplemental = [], []
    for ordinal, original_row in enumerate(original,1):
        record = dict(original_row)
        row_dir = output/'artifacts'/f'row_{ordinal:04d}'
        relative = row_dir.relative_to(output)
        row = {'ordinal':ordinal,'txn_hash':record['txn_hash'],'chain':record['chain']}
        gt = gt_directory/(record['txn_hash']+'.json')
        row['legacy_gt_found'] = gt.is_file()
        if gt.is_file():
            row_dir.mkdir(parents=True,exist_ok=True)
            target = row_dir/'ground_truth.json'
            target.write_bytes(gt.read_bytes())
            record['ground_truth'] = str(relative/'ground_truth.json').replace('\\','/')
            row['legacy_gt_sha256'] = digest_file(gt)
            row['legacy_gt_identity_matches'] = by_filename[gt.name]['filename_identity_matches_payload']
        try:
            urls = json.loads(record.get('analysis') or '[]')
            if not isinstance(urls,list):
                urls = []
        except ValueError:
            urls = []
        row['source_url_candidates'] = [u for u in urls if isinstance(u,str) and urlsplit(u).scheme=='https']
        row['source_urls_are_not_cached_artifacts'] = True
        record['sources'] = []
        for artifact in source_artifacts:
            if record['txn_hash'].lower() not in artifact.get('transaction_hashes',[]):
                continue
            if digest_file(Path(artifact['file'])) != artifact['sha256']:
                raise ValueError('Published source artifact digest mismatch')
            target = row_dir/Path(artifact['file']).name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(Path(artifact['file']).read_bytes())
            record['sources'].append({'url':artifact['url'],'publisher_id':artifact['publisher_id'],
                'artifact':str(target.relative_to(output)).replace('\\','/'),'sha256':digest_file(target)})
        if record['chain']=='eth' and record['txn_hash'].lower() in captured:
            capture,proof,capture_path = captured[record['txn_hash'].lower()]
            row['on_chain_capture'] = {'path':capture_path,**proof}
            for name,data in [('transaction',capture['transaction']),('receipt',capture['canonical_receipt'])]:
                target = row_dir/(name+'.json')
                write(target,data)
                record[name] = str(target.relative_to(output)).replace('\\','/')
            trace = {'transaction_hash':record['txn_hash'],'chain':'eth','complete':True,
                'raw_trace':capture['raw_trace'],'capture_version':capture['capture_version'],
                'tracer_config':{'call':'callTracer','opcode':'Anvil --steps-tracing; stack/storage enabled'}}
            target = row_dir/'trace.json.gz'
            with target.open('wb') as raw:
                with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as compressed:
                    compressed.write(json.dumps(trace).encode())
            record['trace'] = str(target.relative_to(output)).replace('\\','/')
            verification = {'mode':'single-provider-fork-replay','chain_id':1,
                'rpc_endpoints':['configured-dRPC-endpoint'],
                'canonical_block_hash':capture['canonical_receipt']['blockHash'],
                'verified_at':'2026-10-15 client session; recorded replay',
                'tool_versions':{'capture_version':capture['capture_version']},
                'scope':'Local replay plus one RPC provider; no independent second-provider attestation'}
            for name in ['transaction','receipt','trace']:
                verification[name+'_sha256'] = digest_file(output/record[name])
            target = row_dir/'verification.json';write(target,verification)
            record['verification'] = str(target.relative_to(output)).replace('\\','/')
        # No reviewers, adjudicated labels, attackers, source independence or
        # second RPC provider are synthesized from legacy labels or replay.
        rebuilt.append(record)
        supplemental.append(row)
    write(output/'records.json',rebuilt)
    audit = audit_dataset(output/'records.json', output, target=246)
    for result,extra in zip(audit['rows'],supplemental):
        result.update(extra)
        result['decision'] = 'ACCEPTED' if result['accepted'] else 'REJECTED'
    audit.update(original_dataset_sha256=digest_file(source),ground_truth_inventory=inventory,
        unfilled_required_rows=max(0,246-len(original)),
        scope='Full local row rebuild; source links are candidates, legacy GT is unadjudicated',
        legacy_observations={'rows':len(original),'chain_counts':dict(Counter(r['chain'] for r in original)),
            'class_counts':dict(Counter(r.get('class') for r in original)),
            'unique_vulnerability_strings':len({r.get('vuln_type') for r in original}),
            'reentrancy_string_matches':sum('reentran' in r.get('vuln_type','').lower() for r in original)})
    write(output/'row_decisions.json',audit)
    write(output/'accepted_records.json',[r for r,a in zip(rebuilt,audit['rows']) if a['accepted']])
    return audit


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/claim_closure/cohort')
    parser.add_argument('--capture',type=Path,action='append',default=[])
    parser.add_argument('--source-index',type=Path)
    args = parser.parse_args()
    sources = json.loads(args.source_index.read_text())['source_artifacts'] if args.source_index else []
    report = rebuild(ROOT/'benchmark/benchmark_classification_fixed.csv',
                     ROOT/'benchmark/ground_truth',args.output,args.capture,sources)
    print(json.dumps({k:report[k] for k in ['input_rows','accepted_rows','unfilled_required_rows','missing_counts']},indent=2))
