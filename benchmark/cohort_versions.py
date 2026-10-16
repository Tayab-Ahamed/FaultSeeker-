"""Immutable cohort expansion preserving prior experiment isolation.

Only incident, identity, chain and complexity metadata determine assignment.
Publishing copies evidence; it neither measures outcomes nor opens old heldout.json.
"""
from collections import Counter, defaultdict
import csv
import io
import itertools
import json
from pathlib import Path

from benchmark.research_protocol import admit, bind, canonical, identity, read_bound, sha


def extend_split(parent_records, additions, parent_split, incident_aliases, seed=1729):
    """Pin parent memberships and exhaustively place up to 20 new incident groups."""
    if type(seed) is not int or parent_split.get('status') != 'FROZEN':
        raise ValueError('Frozen parent and integer seed required')
    if not isinstance(incident_aliases, dict) or any(not isinstance(k,str) or not k or
            not isinstance(v,str) or not v for k,v in incident_aliases.items()):
        raise ValueError('Explicit nonempty incident aliases required')
    def group(row):
        key=row.get('incident_id') or identity(row)
        seen=set()
        while key in incident_aliases:
            if key in seen:
                raise ValueError('Incident alias cycle')
            seen.add(key); key=incident_aliases[key]
        return key
    # Validate unused aliases too; malformed protocol cannot hide behind absent rows.
    for alias in incident_aliases:
        group({'incident_id':alias})
    rows=sorted(list(parent_records)+list(additions),key=identity)
    ids=[identity(r) for r in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate accepted identity')
    parent_ids=set(map(identity,parent_records))
    train=list(parent_split['train_ids']); heldout=list(parent_split['heldout_ids'])
    if (len(train)!=len(set(train)) or len(heldout)!=len(set(heldout)) or
            set(train)&set(heldout) or set(train)|set(heldout)!=parent_ids or not train or not heldout):
        raise ValueError('Parent membership mismatch')
    pins={}
    for row in parent_records:
        key=group(row); partition=identity(row) in set(train)
        if key in pins and pins[key]!=partition:
            raise ValueError('Parent incident already crosses partitions')
        pins[key]=partition
    groups=defaultdict(list)
    for row in additions:
        key=group(row)
        if key in pins:
            (train if pins[key] else heldout).append(identity(row))
        else:
            groups[key].append(row)
    keys=sorted(groups)
    if len(keys)>20:
        raise ValueError('Safe exhaustive enumeration limit exceeded (20 incident groups)')
    strata=Counter((r['chain'],r.get('complexity_class','UNRECOVERED')) for r in rows)
    by_id={identity(r):r for r in rows}
    baseline=Counter((by_id[i]['chain'],by_id[i].get('complexity_class','UNRECOVERED')) for i in train)
    best=None; best_ids=None
    # Integer tenths avoid floating-point tie artifacts.
    for mask in itertools.product((False,True),repeat=len(keys)):
        picked=[r for key,take in zip(keys,mask) if take for r in groups[key]]
        counts=baseline+Counter((r['chain'],r.get('complexity_class','UNRECOVERED')) for r in picked)
        candidate=sorted(train+[identity(r) for r in picked])
        score=(abs(10*len(candidate)-7*len(rows)),sum(abs(10*counts[s]-7*n) for s,n in strata.items()),
               sha(canonical({'seed':seed,'train_ids':candidate})))
        if best is None or score<best:
            best,best_ids=score,candidate
    train_set=set(best_ids)
    return dict(schema=2,status='FROZEN',seed=seed,train_fraction=.7,heldout_fraction=.3,
        stratification=['chain','complexity_class'],grouping='explicit incident_id aliases, else transaction identity',
        assignment='Immutable parent membership; whole new incident groups minimize global distance, then stratum distance, then seeded SHA-256 tie break; labels excluded',
        incident_aliases=dict(sorted(incident_aliases.items())),train_ids=best_ids,
        heldout_ids=sorted(set(ids)-train_set),strata=[dict(chain=s[0],complexity_class=s[1],total=n,
        train=sum(identity(r) in train_set for r in rows if (r['chain'],r.get('complexity_class','UNRECOVERED'))==s),
        heldout=sum(identity(r) not in train_set for r in rows if (r['chain'],r.get('complexity_class','UNRECOVERED'))==s))
        for s,n in sorted(strata.items())])


def _csv(raw):
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''))
    rows=list(reader)
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or any(None in r or None in r.values() for r in rows):
        raise ValueError('Malformed CSV')
    return reader.fieldnames,rows


def _validate_bindings(value,root):
    """Check nested optional trace/prestate/identity-proof bindings as well."""
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:
            read_bound(value,root)
        for child in value.values():
            _validate_bindings(child,root)
    elif isinstance(value,list):
        for child in value:
            _validate_bindings(child,root)


def publish_extension(root, version_dir, parent_split_binding, addition_manifest_binding, incident_aliases, seed=1729):
    """Validate every source first, then exclusively create a versioned publication.

    Returns bindings to the new manifest and split. Existing publications are never
    overwritten. Parent heldout partition payload is deliberately never opened.
    """
    root=Path(root).resolve(); destination=(root/version_dir).resolve()
    if (not destination.is_relative_to(root) or destination==root or
            '.git' in destination.relative_to(root).parts or any(p.startswith('.env') for p in destination.relative_to(root).parts)):
        raise ValueError('Unsafe publication directory')
    if destination.exists():
        raise ValueError('Publication directory exists')
    split=json.loads(read_bound(parent_split_binding,root))
    manifest_binding=split['manifest']
    if manifest_binding['sha256']!=split['manifest_sha256']:
        raise ValueError('Parent manifest digest disagreement')
    manifest=json.loads(read_bound(manifest_binding,root))
    incoming=json.loads(read_bound(addition_manifest_binding,root))
    if incoming['frozen_study']!=manifest_binding or incoming['frozen_split']!=parent_split_binding:
        raise ValueError('Addition manifest has a different frozen parent')
    old=manifest['records']; additions=[]; accepted_bindings=[]; csv_bindings=[]
    for key,expected in [('original_count',len(old)),('additional_count',len(incoming['additional_records'])),
            ('provenance_complete_unique_available',len(old)+len(incoming['additional_records']))]:
        if key in incoming and (type(incoming[key]) is not int or incoming[key]!=expected):
            raise ValueError('Addition manifest count mismatch: '+key)
    if 'accepted_count' in manifest and manifest['accepted_count']!=len(old):
        raise ValueError('Parent manifest count mismatch')
    fields,csv_rows=_csv(read_bound(manifest['csv'],root))
    if len(csv_rows)!=len(old) or set(map(identity,csv_rows))!=set(map(identity,old)):
        raise ValueError('Parent CSV membership mismatch')
    for item in incoming['additional_records']:
        row=json.loads(read_bound(item['accepted_record'],root))
        if identity(row)!=item['identity']:
            raise ValueError('Addition identity mismatch')
        additions.append(row); accepted_bindings.append(item['accepted_record'])
        path=root/Path(item['accepted_record']['path']).parent/'benchmark_row.csv'
        csv_binding=bind(path,root)
        addition_fields,addition_csv=_csv(read_bound(csv_binding,root))
        if addition_fields!=fields or len(addition_csv)!=1 or identity(addition_csv[0])!=identity(row):
            raise ValueError('Addition CSV membership or schema mismatch')
        values=addition_csv[0]
        receipt=json.loads(read_bound(row['rpc'],root))['receipt']
        raw_gas=receipt.get('gasUsed')
        try:
            if isinstance(raw_gas,bool):
                raise ValueError('Boolean gas value')
            gas=raw_gas if isinstance(raw_gas,int) else int(raw_gas,16)
            if gas<0 or any(values.get(field)!=str(gas) for field in ('gas_used','gas_cost')):
                raise ValueError('Gas disagreement')
        except (TypeError,ValueError):
            raise ValueError('Addition CSV gas does not match bound receipt') from None
        if values.get('class')!=row.get('complexity_class'):
            raise ValueError('Addition CSV complexity does not match accepted record')
        if not row.get('trace') and any(values.get(field)!='' for field in
                ('functioncall_count','unique_functioncall_count','address_count','max_depth')):
            raise ValueError('Addition CSV trace counts require actual trace evidence')
        csv_rows.extend(addition_csv);csv_bindings.append(csv_binding)
    projected=extend_split(old,additions,split,incident_aliases,seed)
    records=sorted(old+additions,key=identity)
    csv_by_id={identity(r):r for r in csv_rows}
    ground_truth={}
    for row in records:
        _validate_bindings(row,root)
        if admit(row,root)['accepted'] is not True:
            raise ValueError('Publication admission rejected: '+identity(row))
        # Copy bound bytes, never infer missing targets or use target labels for assignment.
        ground_truth[identity(row)]=read_bound(row['ground_truth'],root)
        annotation=json.loads(read_bound(row['annotation_record'],root))
        values=csv_by_id[identity(row)]
        if (values.get('vuln_type')!=annotation['vuln_type'] or
                row.get('vulnerability_class')!=annotation['vuln_type']):
            raise ValueError('CSV or record annotation vulnerability mismatch')
        for field in ('is_exploit','reentrancy_label','uncategorized'):
            value=values.get(field,'').casefold()
            if type(annotation.get(field)) is not bool or value not in ('true','false') or (value=='true')!=annotation[field]:
                raise ValueError('CSV annotation boolean mismatch: '+field)
            if field in row and row[field] is not annotation[field]:
                raise ValueError('Record annotation boolean mismatch: '+field)
        for field in ('swc_registry_classification','dasp_classification'):
            if values.get(field)!=annotation.get(field):
                raise ValueError('CSV annotation taxonomy mismatch: '+field)
        gt=json.loads(ground_truth[identity(row)])
        if (gt.get('transaction_hash')!=[row['txn_hash']] or gt.get('chain')!=row['chain'] or
                gt.get('cause')!=annotation['vuln_type'] or gt.get('annotation_record')!=row['annotation_record'] or
                gt.get('is_exploit') is not annotation['is_exploit'] or
                gt.get('reentrancy_label') is not annotation['reentrancy_label']):
            raise ValueError('Ground truth identity or annotation mismatch')
    # No filesystem mutation precedes complete binding, CSV and admission validation.
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.mkdir(exist_ok=False)
    def put(name,raw):
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle:
            handle.write(raw)
        return bind(path,root)
    def js(name,value):
        return put(name,(json.dumps(value,indent=2,ensure_ascii=True)+'\n').encode())
    output=[]
    for row in records:
        row=dict(row)
        row['ground_truth']=put('ground_truth/'+row['chain']+'-'+row['txn_hash']+'.json',ground_truth[identity(row)])
        output.append(row)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
    writer.writerows(sorted(csv_rows,key=identity))
    csv_binding=put('benchmark_classification_fixed.csv',buffer.getvalue().encode())
    publication=dict(schema=3,accepted_count=len(output),target_count=246,target_chains=10,
        remaining_to_target=max(0,246-len(output)),chains=dict(sorted(Counter(r['chain'] for r in output).items())),
        admission_standard=manifest.get('admission_standard','Bound admission standard inherited from parent'),
        not_independent_human_review=True,records=output,csv=csv_binding,
        parent_manifest=manifest_binding,parent_split=parent_split_binding,addition_manifest=addition_manifest_binding,
        accepted_record_bindings=accepted_bindings,addition_csv_bindings=csv_bindings,
        original_ground_truth_bindings={identity(r):r['ground_truth'] for r in records},
        incident_aliases=dict(sorted(incident_aliases.items())),scope='Versioned provenance-complete expansion; no heldout evaluation')
    new_manifest=js('cohort_manifest.json',publication)
    projected.update(manifest=new_manifest,manifest_sha256=new_manifest['sha256'],parent_split=parent_split_binding,
        partitions={name:js('research/'+name+'.json',[r for r in output if identity(r) in set(projected[name+'_ids'])])
                    for name in ('train','heldout')})
    return {'manifest':new_manifest,'split':js('eval_split.json',projected)}
