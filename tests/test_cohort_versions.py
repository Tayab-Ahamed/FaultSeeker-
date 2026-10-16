"""Software-only tests; constructed records are never research evidence."""
import csv
import io
import json
from copy import deepcopy

import pytest

from benchmark.research_protocol import bind, identity, write_json
from benchmark.cohort_versions import extend_split, publish_extension


def record(n, incident=None, chain='eth'):
    return dict(chain=chain, txn_hash='0x'+format(n, '064x'),
                incident_id=incident or 'incident:'+str(n), complexity_class='Moderate')


def test_extension_pins_memberships_and_aliases():
    old = [record(1, 'Orion'), record(2)]
    new = [record(3, 'Orion-BSC', 'bsc'), record(4), record(5), record(6)]
    parent = dict(status='FROZEN', train_ids=[identity(old[1])], heldout_ids=[identity(old[0])])
    result = extend_split(old, new, parent, {'Orion-BSC': 'Orion'})
    assert set(parent['train_ids']) <= set(result['train_ids'])
    assert set(parent['heldout_ids']+[identity(new[0])]) <= set(result['heldout_ids'])
    assert len(result['train_ids']) == 4
    changed = deepcopy(new[::-1])
    for r in changed:
        r['vulnerability_class'] = 'changed label'
        r['reentrancy_label'] = True
    assert result == extend_split(old[::-1], changed, parent, {'Orion-BSC': 'Orion'})


def test_extension_rejects_duplicate_or_conflicting_parent_and_alias_cycle():
    a, b = record(1), record(2)
    p = dict(status='FROZEN', train_ids=[identity(a)], heldout_ids=[identity(b)])
    with pytest.raises(ValueError, match='Duplicate'):
        extend_split([a,b], [a], p, {})
    with pytest.raises(ValueError):
        extend_split([a,b], [], dict(p, heldout_ids=[identity(a)]), {})
    with pytest.raises(ValueError, match='cycle'):
        extend_split([a,b], [], p, {'a':'b','b':'a'})
    with pytest.raises(ValueError, match='incident'):
        extend_split([dict(a,incident_id='x'),dict(b,incident_id='x')], [],p,{})


def test_groups_remain_whole_and_enumeration_is_bounded():
    a,b=record(1),record(2)
    p=dict(status='FROZEN',train_ids=[identity(a)],heldout_ids=[identity(b)])
    c,d=record(3,'shared'),record(4,'shared')
    s=extend_split([a,b],[c,d],p,{})
    assert (identity(c) in s['train_ids']) == (identity(d) in s['train_ids'])
    with pytest.raises(ValueError, match='enumeration'):
        extend_split([a,b],[record(n) for n in range(3,26)],p,{})


def fixture_publication(tmp_path, monkeypatch):
    # Software-only receipt values test numerical consistency, never live admission.
    monkeypatch.setattr('benchmark.cohort_versions.admit', lambda r,root: {'accepted':True})
    old=[record(1),record(2)]
    new=record(3)
    for r in old+[new]:
        annotation=dict(txn_hash=r['txn_hash'],chain=r['chain'],vuln_type='software-test-class',
            is_exploit=True,reentrancy_label=False,uncategorized=True,
            swc_registry_classification='',dasp_classification='')
        annotation_path=tmp_path/f"annotation/{r['txn_hash']}.json"
        write_json(annotation_path,annotation)
        r.update(annotation_record=bind(annotation_path,tmp_path),vulnerability_class='software-test-class',
                 is_exploit=True,reentrancy_label=False)
        path=tmp_path/f"gt/{r['txn_hash']}.json"
        write_json(path, {'transaction_hash':[r['txn_hash']],'chain':r['chain'],'cause':'software-test-class',
                         'annotation_record':r['annotation_record'],'is_exploit':True,'reentrancy_label':False})
        r['ground_truth']=bind(path,tmp_path)
        rpc_path=tmp_path/f"rpc/{r['txn_hash']}.json"
        write_json(rpc_path,{'receipt':{'gasUsed':'0x7b'}})
        r['rpc']=bind(rpc_path,tmp_path)
    fields=['txn_hash','chain','name','vuln_type','is_exploit','reentrancy_label','uncategorized',
            'swc_registry_classification','dasp_classification','gas_used','gas_cost','class',
            'functioncall_count','unique_functioncall_count','address_count','max_depth']
    def csv_bytes(rows):
        out=io.StringIO(newline=''); w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
        for r in rows:
            values=dict(r,vuln_type='software-test-class',uncategorized=True,gas_used='123',gas_cost='123')
            values['class']=r['complexity_class']
            w.writerow({k:values.get(k,'') for k in fields})
        return out.getvalue().encode()
    (tmp_path/'old.csv').write_bytes(csv_bytes(old))
    write_json(tmp_path/'manifest.json',dict(records=old,csv=bind(tmp_path/'old.csv',tmp_path)))
    write_json(tmp_path/'split.json',dict(status='FROZEN',manifest=bind(tmp_path/'manifest.json',tmp_path),
        manifest_sha256=bind(tmp_path/'manifest.json',tmp_path)['sha256'],train_ids=[identity(old[0])],heldout_ids=[identity(old[1])]))
    (tmp_path/'incoming').mkdir()
    write_json(tmp_path/'incoming/accepted_record.json',new)
    (tmp_path/'incoming/benchmark_row.csv').write_bytes(csv_bytes([new]))
    write_json(tmp_path/'additions.json',dict(frozen_study=bind(tmp_path/'manifest.json',tmp_path),
        frozen_split=bind(tmp_path/'split.json',tmp_path),additional_records=[dict(identity=identity(new),accepted_record=bind(tmp_path/'incoming/accepted_record.json',tmp_path))]))
    return bind(tmp_path/'split.json',tmp_path),bind(tmp_path/'additions.json',tmp_path)


def test_publication_preserves_parent_and_binds_exact_gt(tmp_path,monkeypatch):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    original=(tmp_path/'split.json').read_bytes()
    # A dangling sealed-partition payload proves publication never opens it.
    split=json.loads(original)
    split['partitions']={'heldout':{'path':'SEALED_DO_NOT_OPEN.json','sha256':'a'*64}}
    write_json(tmp_path/'split.json',split)
    parent=bind(tmp_path/'split.json',tmp_path)
    incoming=json.loads((tmp_path/'additions.json').read_text())
    incoming['frozen_split']=parent
    write_json(tmp_path/'additions.json',incoming)
    additions=bind(tmp_path/'additions.json',tmp_path)
    original=(tmp_path/'split.json').read_bytes()
    result=publish_extension(tmp_path,'versions/v2',parent,additions,{})
    from benchmark.research_protocol import read_bound
    split=json.loads(read_bound(result['split'],tmp_path))
    manifest=json.loads(read_bound(split['manifest'],tmp_path))
    assert manifest['accepted_count']==3 and split['status']=='FROZEN'
    assert (tmp_path/'split.json').read_bytes()==original
    assert len(json.loads(read_bound(split['partitions']['train'],tmp_path)))==2
    for r in manifest['records']:
        assert read_bound(r['ground_truth'],tmp_path)==(tmp_path/f"gt/{r['txn_hash']}.json").read_bytes()
    with pytest.raises(ValueError,match='exist'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})


def test_publication_validates_everything_before_writing(tmp_path,monkeypatch):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    (tmp_path/'incoming/benchmark_row.csv').write_text('txn_hash,chain,name\nwrong,eth,no\n')
    with pytest.raises(ValueError,match='CSV'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


def test_rejects_failed_admission_and_ground_truth_tampering(tmp_path,monkeypatch):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    monkeypatch.setattr('benchmark.cohort_versions.admit',lambda r,root:{'accepted':False})
    with pytest.raises(ValueError,match='admission rejected'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()
    monkeypatch.setattr('benchmark.cohort_versions.admit',lambda r,root:{'accepted':True})
    next((tmp_path/'gt').iterdir()).write_bytes(b'tampered')
    with pytest.raises(ValueError,match='digest'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


def test_rejects_nested_evidence_tampering_before_publication(tmp_path,monkeypatch):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    evidence=tmp_path/'trace.gz';evidence.write_bytes(b'original software test trace')
    path=tmp_path/'incoming/accepted_record.json'
    row=json.loads(path.read_text());row['trace']=bind(evidence,tmp_path);write_json(path,row)
    incoming=json.loads((tmp_path/'additions.json').read_text())
    incoming['additional_records'][0]['accepted_record']=bind(path,tmp_path)
    write_json(tmp_path/'additions.json',incoming); additions=bind(tmp_path/'additions.json',tmp_path)
    evidence.write_bytes(b'tampered software test trace')
    with pytest.raises(ValueError,match='digest'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


@pytest.mark.parametrize('field,value',[('vuln_type','invented'),('reentrancy_label','True'),
    ('is_exploit','False'),('uncategorized','False'),('swc_registry_classification','SWC-107'),
    ('dasp_classification','Reentrancy')])
def test_csv_labels_must_match_bound_adjudication(tmp_path,monkeypatch,field,value):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    path=tmp_path/'incoming/benchmark_row.csv'
    reader=csv.DictReader(io.StringIO(path.read_text()));fields=reader.fieldnames; rows=list(reader)
    rows[0][field]=value
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    path.write_text(out.getvalue())
    with pytest.raises(ValueError,match='CSV.*annotation'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


@pytest.mark.parametrize('field,value',[('transaction_hash',['0x'+'f'*64]),('chain','bsc'),
    ('cause','invented'),('annotation_record',{'path':'wrong','sha256':'0'*64})])
def test_ground_truth_identity_and_annotation_are_checked(tmp_path,monkeypatch,field,value):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    accepted=tmp_path/'incoming/accepted_record.json';r=json.loads(accepted.read_text())
    gt_path=tmp_path/r['ground_truth']['path'];gt=json.loads(gt_path.read_text());gt[field]=value
    write_json(gt_path,gt);r['ground_truth']=bind(gt_path,tmp_path);write_json(accepted,r)
    incoming=json.loads((tmp_path/'additions.json').read_text())
    incoming['additional_records'][0]['accepted_record']=bind(accepted,tmp_path)
    write_json(tmp_path/'additions.json',incoming);additions=bind(tmp_path/'additions.json',tmp_path)
    with pytest.raises(ValueError,match='Ground truth'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


def test_manifest_counts_are_checked(tmp_path,monkeypatch):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    path=tmp_path/'additions.json';incoming=json.loads(path.read_text());incoming['additional_count']=99
    write_json(path,incoming);additions=bind(path,tmp_path)
    with pytest.raises(ValueError,match='count'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()


@pytest.mark.parametrize('field,value',[('gas_used','999'),('gas_cost','999'),('class','Complex'),
    ('functioncall_count','1'),('unique_functioncall_count','1'),('address_count','1'),('max_depth','0')])
def test_addition_numeric_metadata_requires_evidence(tmp_path,monkeypatch,field,value):
    parent,additions=fixture_publication(tmp_path,monkeypatch)
    path=tmp_path/'incoming/benchmark_row.csv'
    reader=csv.DictReader(io.StringIO(path.read_text()));fields=reader.fieldnames;rows=list(reader)
    rows[0][field]=value
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    path.write_text(out.getvalue())
    with pytest.raises(ValueError,match='CSV.*(gas|complexity|trace)'):
        publish_extension(tmp_path,'versions/v2',parent,additions,{})
    assert not (tmp_path/'versions').exists()
    with pytest.raises(ValueError,match='digest'):
        publish_extension(tmp_path,'versions/v2',dict(parent,sha256='0'*64),additions,{})
    assert not (tmp_path/'versions').exists()
