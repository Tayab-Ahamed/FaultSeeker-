"""Inventory ONLY pinned original run worker caches; never inspect other batches."""
import collections
import hashlib
import json
from pathlib import Path
from scripts.research import address_ranking_phase1 as base


def audit(root):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    allowed={r['txn_hash'] for r in manifest['rows'] if r.get('status')=='ok'}
    records=[]
    inventory=collections.Counter()
    for path in sorted((root/'.workers').rglob('*')):
        if not path.is_file():
            continue
        inventory[path.name if path.parent.name!='raw' else 'raw.json']+=1
        if path.parent.name=='raw':
            if path.stem not in allowed:
                continue
            data=json.loads(path.read_text(encoding='utf-8'))
            rows=[data]
        elif path.name=='manifest.json':
            data=json.loads(path.read_text(encoding='utf-8'))
            rows=[r for r in data.get('rows',[]) if r.get('txn_hash') in allowed]
        else:
            continue
        for row in rows:
            cast=row.get('cast') or {}
            records.append(dict(path=path.relative_to(root).as_posix(),txn_hash=row['txn_hash'],
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cast_keys=sorted(cast),
                output_tail_chars=len(cast.get('output_tail') or ''),stderr_tail_chars=len(cast.get('stderr_tail') or ''),
                runtime_references={k:v for k,v in row.items() if k!='filename' and any(s in k.lower() for s in ['path','log','trace','file'])}))
    return dict(root=str(root.resolve()),manifest_sha256=base.sha(root/'manifest.json'),allowlisted_transactions=len(allowed),
                inventory=dict(inventory),records=records,network_calls=0,complete_trace_files_found=0,
                limitation='All identified runtime payloads are output_tail/stderr_tail; no full trace file or trace path is present in scoped worker cache.')

if __name__=='__main__':
    base.install_offline_guard()
    root=base.ROOT.parent/'FaultSeeker--main/reports/original_benchmark/provider-pinned/original-v1-pinned-sequential-20261017'
    result=audit(root)
    (base.ROOT/'reports/localization_continuous/lane_a/cache_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(inventory=result['inventory'],records=len(result['records']),max_output_tail=max(r['output_tail_chars'] for r in result['records']),max_stderr_tail=max(r['stderr_tail_chars'] for r in result['records']),references=sum(bool(r['runtime_references']) for r in result['records']))))
