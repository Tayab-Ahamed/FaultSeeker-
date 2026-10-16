"""Export real bound TRAIN storage-PC/source evidence; no model or quality scores."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.modules.setdefault('readline',None)
from benchmark.research_protocol import bind,read_bound,write_json,append_experiment,load_train,identity
from benchmark.verified_source_inputs import VerifiedSourceDownloader
from scripts.run_train_production import no_network
from scripts.run_authentic_research import system_identity,snapshot_system

def run(root=ROOT):
 root=Path(root);base=root/'reports/cohort_rebuild_v2'
 evidence_binding=bind(base/'localization_sources/evidence.json',root)
 evidence=json.loads(read_bound(evidence_binding,root))
 split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
 train={identity(row) for row in load_train(split,root)}
 out=base/'execution_source_spans'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
 out.mkdir(parents=True,exist_ok=False)
 system=system_identity([Path(__file__),root/'benchmark/verified_source_inputs.py',root/'benchmark/execution_source_inputs.py'])
 write_json(out/'system.json',system);snapshot=snapshot_system(system,out)
 config={'experiment':'observed-storage-PC-source-evidence-v1','input_sources':evidence_binding,'system':bind(out/'system.json',root),'source_snapshot':bind(snapshot,root),'scope':'Executed source spans are not AST function slices or vulnerability attribution'}
 common={'run_id':out.name,'seed':split['seed'],'config':config,'sample_ids':[],'metrics':None}
 log=base/'experiments_log.json'
 append_experiment(log,split,dict(common,kind='dispatch-input-evidence-train'))
 records=[]
 ledger=root/'data/research/spend_ledger.json';before=ledger.read_bytes()
 with no_network() as attempts:
  for case in evidence['cases']:
   key=case['identity']
   if key not in train:raise ValueError('Source case is outside frozen TRAIN')
   addresses=[c['address'] for c in case['contracts'] if c.get('response')]
   if not addresses:continue
   create=VerifiedSourceDownloader.factory(root=root,evidence_binding=evidence_binding,train_identity=key,include_execution_spans=True)
   downloader=create(key.split(':',1)[0],addresses);mapping=downloader.run()
   report=downloader.execution_evidence
   report['identity']=key
   report['source_provenance']=downloader.provenance
   path=out/(key.replace(':','-')+'.json');write_json(path,report)
   records.append({'identity':key,'evidence':bind(path,root),'summary':report['summary'],'ABI_selectors_with_executed_spans':sum(any(record.get('executed_source_spans') for record in bundle) for functions in mapping.values() for bundle in functions.values())})
 if ledger.read_bytes()!=before:raise RuntimeError('Real spend ledger changed during offline export')
 if attempts[0]:raise RuntimeError('Offline export attempted network')
 summary={'scope':config['scope'],'config':config,'records':records,'metrics':None,'quality_experiment':False,'new_network_requests':0,'network_attempts':attempts[0],'real_spend_ledger_unchanged':True,'heldout_used':False,'source_map_reference':'https://docs.soliditylang.org/en/latest/internals/source_mappings.html','limitations':['Entry selector groups observed execution, not AST function ownership','Generated/unmapped/missing runtime source remains explicit','Known verbatim builtin maps are unreliable and excluded','No fault causality or ranking improvement is inferred']}
 write_json(out/'summary.json',summary)
 append_experiment(log,split,dict(common,kind='recorded-input-evidence-train',evidence=bind(out/'summary.json',root)))
 print(json.dumps({'run_id':out.name,'records':[{'identity':r['identity'],'summary':r['summary'],'selectors_with_spans':r['ABI_selectors_with_executed_spans']} for r in records],'network_attempts':attempts[0],'ledger_unchanged':True}))
 return summary

if __name__=='__main__':run()
