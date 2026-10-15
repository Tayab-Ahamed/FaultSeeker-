import csv
import json
from pathlib import Path

import pytest


def fixture_record(root,ordinal):
    from benchmark.research_protocol import bind,write_json
    tx='0x'+format(ordinal,'064x');block='0x'+'b'*64
    rpc=root/f'rpc-{ordinal}.json'
    write_json(rpc,{'mode':'live-rpc','txn_hash':tx,'chain':'eth','chain_id':1,
       'transaction':{'hash':tx,'chainId':'0x1','blockHash':block},
       'receipt':{'transactionHash':tx,'blockHash':block,'status':'0x1','gasUsed':'0x5208'}})
    sources=[];observations=[]
    for i,quote in enumerate(['The callback permits reentrancy before the account balance is updated.',
                              'An external receiver reenters the withdrawal before its balance update.']):
        path=root/f'source-{ordinal}-{i}.txt';path.write_text(quote)
        artifact=bind(path,root);publisher=f'publisher-{i}'
        sources.append({'publisher_id':publisher,'independence_group':publisher,'artifact':artifact,
            'url':f'https://security-{i}.example/report/{ordinal}','review_status':'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED',
            'independence_basis':'Independent original analyses in this unit fixture','identity_basis':tx})
        observations.append({'publisher_id':publisher,'source_artifact':artifact,'vulnerability_class':'Reentrancy','mechanism_excerpt':quote})
    annotation=root/f'annotation-{ordinal}.json'
    write_json(annotation,{'mode':'public-source-consensus-v1','adjudication_author':'Codex','txn_hash':tx,'chain':'eth',
        'is_exploit':True,'vuln_type':'Reentrancy','uncategorized':False,'reentrancy_label':True,
        'swc_registry_classification':'SWC-107','dasp_classification':'Reentrancy',
        'adjudication_basis':'Two source mechanisms agree in this unit fixture','independent_observations':observations})
    return {'txn_hash':tx,'chain':'eth','incident_id':f'incident-{ordinal}','sources':sources,
            'rpc':bind(rpc,root),'annotation_record':bind(annotation,root)}


def test_publication_revalidates_admission_before_changing_active_data(tmp_path):
    from scripts.publish_authentic_cohort import publish
    row=fixture_record(tmp_path,1);row['rpc']['sha256']='0'*64
    with pytest.raises(ValueError,match='admission'):
        publish(tmp_path,[row],{'rows':[]})
    assert not (tmp_path/'benchmark').exists()


def test_original_ground_truth_duplicates_are_preserved_by_filename_and_hash(tmp_path):
    from scripts.publish_authentic_cohort import preserve_legacy
    bench=tmp_path/'benchmark';gt=bench/'ground_truth';gt.mkdir(parents=True)
    (bench/'benchmark_classification_fixed.csv').write_text('txn_hash,chain\noriginal,eth\n')
    for name in ['original.json','duplicate-name.json']:
        (gt/name).write_text('{"transaction_hash":["same-identity"]}')
    inventory=preserve_legacy(tmp_path)
    assert len(inventory['ground_truth'])==2
    for item in inventory['ground_truth']:
        assert (tmp_path/item['archive']['path']).read_bytes()==(tmp_path/item['original']['path']).read_bytes()


def test_published_manifest_split_and_csv_are_pinned_and_cannot_be_refrozen(tmp_path):
    from scripts.publish_authentic_cohort import publish
    from benchmark.research_protocol import read_bound,load_train
    rows=[fixture_record(tmp_path,i) for i in (1,2)]
    result=publish(tmp_path,rows,{'rows':[]})
    manifest=json.loads(read_bound(result['manifest'],tmp_path))
    split=json.loads(read_bound(result['split'],tmp_path))
    assert manifest['accepted_count']==2
    assert len(split['train_ids'])==len(split['heldout_ids'])==1
    assert len(load_train(split,tmp_path))==1
    assert len(list((tmp_path/'benchmark/ground_truth').glob('*.json')))==2
    data=list(csv.DictReader((tmp_path/'benchmark/benchmark_classification_fixed.csv').open()))
    assert {r['txn_hash'] for r in data}=={r['txn_hash'] for r in rows}
    assert all(r['class']=='UNRECOVERED' for r in data)
    before=(tmp_path/'benchmark/eval_split.json').read_bytes()
    with pytest.raises(FileExistsError):publish(tmp_path,rows,{'rows':[]})
    assert (tmp_path/'benchmark/eval_split.json').read_bytes()==before
