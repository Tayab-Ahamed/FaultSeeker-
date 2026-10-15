"""Publish only revalidated evidence; preserve originals and freeze one split.

This does not establish the published 246-row cohort or performance numbers.
Unavailable localization targets remain explicitly unavailable, never negatives.
"""
from collections import Counter
from datetime import datetime, timezone
import csv
import gzip
import io
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from benchmark.research_protocol import admit, bind, identity, make_split, read_bound, sha, write_json

BASE=Path('reports/cohort_rebuild_v2')
FUNCTION_NAMES=('_doSwapTokens','donateToReserves','depositAdditionalToFNFT','borrowFresh',
                '_burn','_transferFeesSupportingTaxTokens','submit','routerCallNative')
FIELDS=('txn_hash','chain','name','functioncall_count','unique_functioncall_count','address_count',
        'max_depth','gas_cost','gas_used','class','vuln_type','swc_registry_classification',
        'dasp_classification','uncategorized','is_exploit','reentrancy_label','annotation_mode','analysis')


def preserve_legacy(root):
    root=Path(root).resolve()
    folder=root/BASE/'quarantine/original_active'
    inventory_path=folder/'inventory.json'
    if inventory_path.exists():
        inventory=json.loads(inventory_path.read_text())
        for entry in inventory['ground_truth']+([inventory['csv']] if inventory.get('csv') else []):
            read_bound(entry['archive'],root)
        return inventory
    inventory={'ground_truth':[],'csv':None}
    files=list((root/'benchmark/ground_truth').glob('*.json'))
    csv_path=root/'benchmark/benchmark_classification_fixed.csv'
    if csv_path.exists():
        files.append(csv_path)
    for path in files:
        if not path.resolve().is_relative_to(root):
            raise ValueError('Legacy path escapes workspace')
        relative=path.relative_to(root/'benchmark')
        target=folder/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=path.read_bytes()
        if target.exists() and target.read_bytes()!=raw:
            raise ValueError('Refusing to overwrite original archive')
        target.write_bytes(raw)
        if target.read_bytes()!=raw:
            raise ValueError('Original archive verification failed')
        entry={'original':bind(path,root),'archive':bind(target,root)}
        if path==csv_path:
            inventory['csv']=entry
        else:
            inventory['ground_truth'].append(entry)
    write_json(inventory_path,inventory)
    return inventory


def ground_truth(row,annotation):
    names=[]
    for observation in annotation['independent_observations']:
        quote=observation['mechanism_excerpt']
        for name in FUNCTION_NAMES:
            if re.search(r'(?<![A-Za-z0-9_])'+re.escape(name)+r'(?![A-Za-z0-9_])',quote):
                names.append({'name':name,'address':None,'signature':None,'line':None,
                    'source':observation['source_artifact'],'evidence_excerpt':quote,
                    'status':'SOURCE_SUPPORTED_NAME; ADDRESS_SIGNATURE_AND_LINE_NOT_VERIFIED'})
    return {'schema':2,'name':row.get('incident_id','').removeprefix('reviewed:'),
        'transaction_hash':[row['txn_hash']],'chain':row['chain'],'cause':annotation['vuln_type'],
        'annotation_mode':annotation['mode'],'independent_human_review':False,
        'annotation_record':row['annotation_record'],'is_exploit':True,
        'reentrancy_label':annotation['reentrancy_label'],'location':{},'findings':[],
        'source_supported_functions':names,
        'localization_status':'UNAVAILABLE: no independently source-bound address/signature/line targets established; historical GT is archived separately'}


def prepare_records(root,records):
    root=Path(root).resolve()
    prepared=[]
    seen=set()
    for original in sorted(records,key=identity):
        row=dict(original)
        if identity(row) in seen or not admit(row,root)['accepted']:
            raise ValueError('Duplicate or invalid admission; active data remains unchanged')
        seen.add(identity(row))
        annotation=json.loads(read_bound(row['annotation_record'],root))
        rpc=json.loads(read_bound(row['rpc'],root))
        result={k:row[k] for k in ('txn_hash','chain','incident_id','rpc','sources','annotation_record')}
        result.update(is_exploit=True,reentrancy_label=annotation['reentrancy_label'],
            vulnerability_class=annotation['vuln_type'],complexity_class='UNRECOVERED',
            membership=row.get('membership','SOURCE-REVIEWED-ADMISSION'))
        data={key:'' for key in FIELDS}
        gas=rpc['receipt'].get('gasUsed')
        gas_used=int(gas,16) if isinstance(gas,str) and gas.startswith('0x') else gas
        data.update(txn_hash=row['txn_hash'],chain=row['chain'],name=row['incident_id'].removeprefix('reviewed:'),
            gas_cost=gas_used,gas_used=gas_used,**{'class':'UNRECOVERED'},vuln_type=annotation['vuln_type'],
            swc_registry_classification=annotation.get('swc_registry_classification',''),
            dasp_classification=annotation.get('dasp_classification',''),uncategorized=annotation['uncategorized'],
            is_exploit=True,reentrancy_label=annotation['reentrancy_label'],annotation_mode=annotation['mode'],
            analysis=json.dumps([s['url'] for s in row['sources']]))
        trace=root/BASE/'traces'/row['chain']/(row['txn_hash']+'.json.gz')
        if trace.exists():
            capture=json.loads(gzip.decompress(trace.read_bytes()))
            if capture.get('transaction_hash')!=row['txn_hash'] or capture.get('chain')!=row['chain']:
                raise ValueError('Trace identity mismatch')
            from scripts.capture_authentic_traces import walk,validate_call_identity
            validate_call_identity(capture['raw_trace']['call'],rpc['transaction'],rpc['receipt'])
            result['trace']=bind(trace,root)
            if capture.get('prestate_artifact'):
                read_bound(capture['prestate_artifact'],root)
                result['prestate']=capture['prestate_artifact']
            complexity=capture.get('complexity',{})
            result['complexity_class']=complexity.get('complexity_class','UNRECOVERED')
            nodes=list(walk(capture['raw_trace']['call']))
            def depth(node):
                return 1+max((depth(c) for c in node.get('calls',[])),default=0)
            data.update(functioncall_count=len(nodes),unique_functioncall_count=complexity.get('unique_function_calls',''),
                address_count=len({f.get(k,'').lower() for f in nodes for k in ('from','to') if f.get(k)}),
                max_depth=depth(capture['raw_trace']['call'])-1,**{'class':result['complexity_class']})
        prepared.append((result,data,ground_truth(row,annotation)))
    if not prepared:
        raise ValueError('No accepted cohort; refusing to replace active data')
    return prepared


def publish(root,records,decisions):
    root=Path(root).resolve()
    benchmark=root/'benchmark'
    manifest_path=benchmark/'cohort_manifest.json'
    split_path=benchmark/'eval_split.json'
    if manifest_path.exists() or split_path.exists():
        raise FileExistsError('Cohort/split already frozen; refusing to refreeze')
    prepared=prepare_records(root,records)
    # All source/RPC bindings are validated before the first active-data mutation.
    inventory=preserve_legacy(root)
    folder=root/BASE
    rejected=[r for r in decisions.get('rows',[]) if not r.get('accepted')]
    write_json(folder/'quarantine/row_decisions.json',{'rows':rejected,
        'scope':'Rejected under current acquired evidence; not proof that corroboration can never be found'})
    benchmark.mkdir(parents=True,exist_ok=True)
    ground=benchmark/'ground_truth'
    ground.mkdir(exist_ok=True)
    # Exact files only, with verified archives; never recursive deletion.
    for entry in inventory['ground_truth']:
        original=(root/entry['original']['path']).resolve()
        if not original.is_relative_to(ground.resolve()):
            raise ValueError('Ground-truth path escapes intended directory')
        if original.exists():
            if sha(original.read_bytes())!=entry['archive']['sha256']:
                raise ValueError('Original changed after archive; publication refused')
            original.unlink()
    published=[]
    for row,data,gt in prepared:
        target=ground/(row['txn_hash']+'.json')
        if target.exists():
            raise ValueError('Ground-truth identity collision')
        write_json(target,gt)
        row['ground_truth']=bind(target,root)
        published.append(row)
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator='\n')
    writer.writeheader();writer.writerows(data for row,data,gt in prepared)
    csv_path=benchmark/'benchmark_classification_fixed.csv'
    csv_path.write_bytes(stream.getvalue().encode())
    manifest={'schema':2,'created_at':datetime.now(timezone.utc).isoformat(),
        'admission_standard':'RPC transaction/receipt identity, two independent security-publisher artifacts, Codex public-source-consensus adjudication',
        'not_independent_human_review':True,'target_count':246,'accepted_count':len(published),
        'target_chains':10,'chains':dict(Counter(r['chain'] for r in published)),
        'remaining_to_target':max(0,246-len(published)),'records':published,'csv':bind(csv_path,root),
        'quarantine':bind(folder/'quarantine/row_decisions.json',root),
        'original_active_inventory':bind(folder/'quarantine/original_active/inventory.json',root),
        'measurement_definitions':{'gas_cost':'Receipt gasUsed in gas units, not USD',
            'functioncall_count':'All callTracer frames','unique_functioncall_count':'Code-verified address/selector pairs',
            'max_depth':'Root depth is zero','UNRECOVERED':'Unavailable evidence; never copied from a historical CSV class'}}
    write_json(manifest_path,manifest)
    manifest_binding=bind(manifest_path,root)
    (benchmark/'cohort_manifest.sha256').write_bytes((manifest_binding['sha256']+'  cohort_manifest.json\n').encode())
    split=make_split(published,manifest_binding['sha256'],seed=1729)
    split['manifest']=manifest_binding
    split['limitations']=['Small/singleton strata cannot all have exact 70/30 representation.',
        'UNRECOVERED is an explicit missing-complexity stratum, not an inferred complexity class.',
        'Labels were adjudicated before the freeze; model tuning and evaluation have not run.']
    partitions={}
    for name in ('train','heldout'):
        ids=set(split[name+'_ids'])
        path=benchmark/'research'/f'{name}.json'
        write_json(path,[r for r in published if identity(r) in ids])
        partitions[name]=bind(path,root)
    split['partitions']=partitions
    write_json(split_path,split)
    return {'manifest':manifest_binding,'split':bind(split_path,root),
            'accepted_count':len(published),'train_count':len(split['train_ids']),'heldout_count':len(split['heldout_ids'])}


if __name__=='__main__':
    result=publish(ROOT,json.loads((ROOT/BASE/'admitted_records.json').read_text()),
                   json.loads((ROOT/BASE/'row_decisions.json').read_text()))
    write_json(ROOT/BASE/'publication.json',result)
    print(json.dumps(result))
