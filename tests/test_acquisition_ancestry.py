"""Software-only ancestry isolation tests, not empirical research outcomes."""
import json
from pathlib import Path
import pytest
from benchmark.research_protocol import bind,sha,write_json,load_acquisition_indexes
from tests.test_versioned_train_inputs import versioned_workspace,guard_heldout_reads


def ancestry(root):
    original,added,parent=versioned_workspace(root)
    spec=json.loads(parent.read_text())
    leaf=root/'benchmark/versions/leaf/eval_split.json'
    child=dict(spec,parent_split=bind(parent,root))
    write_json(leaf,child)
    def index(split,record):
        binding=bind(split,root)
        directory=root/'reports/cohort_rebuild_v2/acquisitions'/binding['sha256']
        snapshot=directory/'snapshot.json'
        write_json(snapshot,{'split':binding,'attempts':[record]})
        write_json(directory/'trace_acquisition_train.json',{'split':binding,'snapshot':bind(snapshot,root)})
        return snapshot
    record={'identity':spec['train_ids'][0],'artifact':{'path':'NEVER_OPEN_CAPTURE.json','sha256':'0'*64}}
    snap=index(parent,record)
    return parent,leaf,record,snap,index


def test_leaf_inherits_parent_snapshot_without_opening_capture_or_heldout(tmp_path,monkeypatch):
    parent,leaf,record,snapshot,_=ancestry(tmp_path)
    guard_heldout_reads(monkeypatch)
    records,bindings=load_acquisition_indexes(tmp_path,leaf)
    assert records['trace'][record['identity']]==record
    assert bind(snapshot,tmp_path) in bindings


def test_failed_leaf_preserves_parent_capture_and_leaf_success_overrides(tmp_path,monkeypatch):
    _,leaf,record,_,index=ancestry(tmp_path)
    failed={'identity':record['identity'],'status':'UNAVAILABLE'}
    index(leaf,failed)
    guard_heldout_reads(monkeypatch)
    assert load_acquisition_indexes(tmp_path,leaf)[0]['trace'][record['identity']]==record
    success=dict(record,artifact={'path':'leaf.json','sha256':'1'*64})
    index(leaf,success)
    assert load_acquisition_indexes(tmp_path,leaf)[0]['trace'][record['identity']]==success


@pytest.mark.parametrize('change',['drop-train','drop-heldout','swap-partitions'])
def test_parent_membership_is_immutable_even_if_leaf_manifest_consistent(tmp_path,change):
    parent,leaf,_,_,_=ancestry(tmp_path)
    child=json.loads(leaf.read_text())
    if change=='swap-partitions':
        child['train_ids'],child['heldout_ids']=child['heldout_ids'],child['train_ids']
        manifest=json.loads((tmp_path/child['manifest']['path']).read_text())
        train_rows=[row for row in manifest['records'] if row['chain']+':'+row['txn_hash'] in child['train_ids']]
        write_json(leaf.parent/'train.json',train_rows)
        child['partitions']=dict(child['partitions'],train=bind(leaf.parent/'train.json',tmp_path))
    else:
        field='train_ids' if change=='drop-train' else 'heldout_ids'
        child[field]=[]
    write_json(leaf,child)
    with pytest.raises(ValueError):load_acquisition_indexes(tmp_path,leaf)


def test_tampered_parent_binding_rejected_before_index(tmp_path):
    parent,leaf,_,_,_=ancestry(tmp_path)
    parent.write_bytes(parent.read_bytes()+b' ')
    with pytest.raises(ValueError,match='digest'):load_acquisition_indexes(tmp_path,leaf)


def test_parent_snapshot_must_match_its_own_split(tmp_path):
    _,leaf,_,snapshot,_=ancestry(tmp_path)
    data=json.loads(snapshot.read_text());data['split']=bind(leaf,tmp_path)
    write_json(snapshot,data)
    pointer=snapshot.parent/'trace_acquisition_train.json'
    wrapper=json.loads(pointer.read_text());wrapper['snapshot']=bind(snapshot,tmp_path);write_json(pointer,wrapper)
    with pytest.raises(ValueError,match='split'):load_acquisition_indexes(tmp_path,leaf)


def test_parent_path_cycle_rejected_before_unbound_body(tmp_path):
    _,leaf,_,_,_=ancestry(tmp_path)
    child=json.loads(leaf.read_text())
    child['parent_split']={'path':leaf.relative_to(tmp_path).as_posix(),'sha256':'0'*64}
    write_json(leaf,child)
    with pytest.raises(ValueError,match='cycle'):load_acquisition_indexes(tmp_path,leaf)


@pytest.mark.parametrize('bad',['manifest','snapshot','owner-membership'])
def test_ancestor_evidence_failure_is_not_silently_ignored(tmp_path,bad):
    parent,leaf,record,snapshot,_=ancestry(tmp_path)
    if bad=='manifest':
        parent_spec=json.loads(parent.read_text())
        path=tmp_path/parent_spec['manifest']['path']
        path.write_bytes(path.read_bytes()+b' ')
    elif bad=='snapshot':
        snapshot.write_bytes(snapshot.read_bytes()+b' ')
    else:
        parent_spec=json.loads(parent.read_text())
        payload=json.loads(snapshot.read_text())
        payload['attempts'][0]['identity']=parent_spec['heldout_ids'][0]
        write_json(snapshot,payload)
        pointer=snapshot.parent/'trace_acquisition_train.json'
        wrapper=json.loads(pointer.read_text());wrapper['snapshot']=bind(snapshot,tmp_path);write_json(pointer,wrapper)
    with pytest.raises(ValueError):load_acquisition_indexes(tmp_path,leaf)


def test_ancestry_merge_keeps_opcode_precedence_and_immutable_index_bindings(tmp_path,monkeypatch):
    parent,leaf,record,parent_snapshot,_=ancestry(tmp_path)
    owner=bind(leaf,tmp_path)
    directory=tmp_path/'reports/cohort_rebuild_v2/acquisitions'/owner['sha256']
    opcode=dict(record,artifact={'path':'opcode.json.gz','sha256':'f'*64})
    snapshot=directory/'opcode-snapshot.json'
    write_json(snapshot,{'split':owner,'attempts':[opcode]})
    write_json(directory/'opcode_acquisition_train.json',{'split':owner,'snapshot':bind(snapshot,tmp_path)})
    guard_heldout_reads(monkeypatch)
    data,bindings=load_acquisition_indexes(tmp_path,leaf)
    assert data['opcode'][record['identity']]==opcode
    assert data['trace'][record['identity']]==record
    assert bind(parent_snapshot,tmp_path) in bindings and bind(snapshot,tmp_path) in bindings
    # Metadata selection does not read either intentionally absent capture body.
    assert not (tmp_path/'opcode.json.gz').exists()


@pytest.mark.parametrize('removed',['train_ids','heldout_ids'])
def test_parent_ids_cannot_disappear_under_consistent_rehashed_leaf_manifest(tmp_path,removed):
    _,leaf,_,_,_=ancestry(tmp_path)
    child=json.loads(leaf.read_text())
    removed_ids=set(child[removed])
    manifest=json.loads((tmp_path/child['manifest']['path']).read_text())
    manifest['records']=[r for r in manifest['records'] if r['chain']+':'+r['txn_hash'] not in removed_ids]
    manifest['accepted_count']=len(manifest['records'])
    manifest_path=leaf.parent/'cohort_manifest.json';write_json(manifest_path,manifest)
    child['manifest']=bind(manifest_path,tmp_path);child['manifest_sha256']=child['manifest']['sha256']
    child[removed]=[]
    train_rows=[r for r in manifest['records'] if r['chain']+':'+r['txn_hash'] in child['train_ids']]
    write_json(leaf.parent/'train.json',train_rows)
    child['partitions']['train']=bind(leaf.parent/'train.json',tmp_path)
    write_json(leaf,child)
    with pytest.raises(ValueError,match='preserved'):load_acquisition_indexes(tmp_path,leaf)
