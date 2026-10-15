"""Preregistered bounded real cloud-only TRAIN function-analysis experiment."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
import math
import os
from pathlib import Path
import sys
import uuid
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.modules.setdefault('readline',None)
from benchmark.research_protocol import bind,read_bound,write_json,load_train,append_experiment
from benchmark.nara_pilot_provider import NaraPilot,StudyStop,MODEL
from benchmark.verified_source_inputs import VerifiedSourceDownloader
from benchmark.captured_inputs import load_train_inputs
from faultseeker.core.llm_router import HybridLLMRouter,COST_RATES
from faultseeker.core.spend_guard import SpendGuard,BudgetApprovalRequired
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.function_analysis.function_ranker import FunctionRanker
from scripts.run_authentic_research import system_identity,snapshot_system
from scripts.run_train_production import no_network
BASE=Path('reports/cohort_rebuild_v2')

def configuration(root=ROOT):
    root=Path(root);base=root/BASE
    protocol=json.loads((base/'provider_pilot/protocol.json').read_text(encoding='utf-8'))
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    train={r['chain']+':'+r['txn_hash'] for r in load_train(split,root)}
    if not set(protocol['train_identities'])<=train or len(protocol['train_identities'])!=2:raise ValueError('Pilot requires two frozen TRAIN identities')
    if protocol['model_alias']!=MODEL or protocol['max_calls']!=20 or protocol['completion_cap']!=4096:raise ValueError('Preregistered model/request policy mismatch')
    price=json.loads(read_bound(protocol['pricing'],root))
    catalog=json.loads(read_bound(price['catalog'],root))
    model=next(m for m in catalog['data'] if m['id']==MODEL)
    if price['http_status']!=200 or model!=price['model']:raise ValueError('Catalog identity mismatch')
    fx=json.loads(read_bound(protocol['fx'],root));xml=ET.fromstring(read_bound(fx['source'],root))
    currencies={n.attrib['currency']:float(n.attrib['rate']) for n in xml.iter() if 'currency' in n.attrib}
    date=next(n.attrib['time'] for n in xml.iter() if 'time' in n.attrib)
    actual=currencies['IDR']/currencies['USD'];floor=fx['budget_idr_per_usd']
    if date!=fx['reference_date'] or not math.isclose(actual,fx['observed_idr_per_usd']) or not 0<floor<=actual:raise ValueError('Invalid bound FX evidence')
    rates={'input':float(model['input_idr_per_1m'])/floor,'output':float(model['output_idr_per_1m'])/floor}
    if any(not math.isfinite(v) or v<=0 for v in rates.values()):raise ValueError('Unknown/invalid conservative pricing')
    read_bound(protocol['source_inputs'],root)
    return protocol,rates

def approved_call_cap(approval,protocol_binding):
    cap=approval.get('max_completion_requests')
    if (approval.get('approved') is not True or type(cap) is not int or not 1<=cap<=20
            or approval.get('protocol')!=protocol_binding
            or approval.get('destination')!='https://router.bynara.id/v1/chat/completions'
            or approval.get('stop_on_any_error') is not True):
        raise ValueError('Explicit approved bounded pilot scope missing or changed')
    if 'aggregate_pilot_limit' in approval:
        prior=approval.get('previous_completion_requests')
        if (approval['aggregate_pilot_limit']!=20 or type(prior) is not int
                or not 0<=prior<=20 or prior+cap>20):
            raise ValueError('Combined pilot completion ceiling would be exceeded')
    return cap


def claim_dispatch(path,approval,run_id,max_calls=20):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle:
        json.dump({'run_id':run_id,'approval':approval,'max_completion_requests':max_calls},handle,indent=2)
        handle.flush();os.fsync(handle.fileno())

def run(root=ROOT,live=False,approval_file=None):
    if not live:raise ValueError('Explicit --live required before credentials or dispatch')
    root=Path(root);base=root/BASE;protocol,rates=configuration(root)
    approval_path=Path(approval_file).resolve() if approval_file else base/'provider_pilot/approval.json'
    if approval_path.parent.resolve()!=(base/'provider_pilot').resolve():
        raise ValueError('Approval must be a reviewed provider_pilot artifact')
    approval=json.loads(approval_path.read_text(encoding='utf-8'))
    max_calls=approved_call_cap(approval,bind(base/'provider_pilot/protocol.json',root))
    if approval.get('prior_batch'):
        prior_name=approval['prior_batch']
        import re
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{8}',prior_name):
            raise ValueError('Invalid previous batch identity')
        prior=json.loads((base/'gateway_runs'/prior_name/'summary.json').read_text(encoding='utf-8'))
        if prior['completion_requests']!=approval.get('previous_completion_requests'):
            raise ValueError('Previous request count differs from actual stopped batch')

    permit_path=(base/'provider_pilot/dispatch_permit.json' if approval_path.name=='approval.json'
                 else approval_path.with_name(approval_path.stem+'.dispatch_permit.json'))
    if permit_path.exists():raise ValueError('Approved dispatch permit already consumed')
    from dotenv import dotenv_values
    values={}
    for path in (Path(r'C:\Users\91701\Downloads\Wingman-main\Wingman-main\.env'),root/'.env'):
        if path.exists():values.update({k:v for k,v in dotenv_values(path).items() if v})
    key=values.get('BYNARA_API_KEY')
    if not key:raise ValueError('BYNARA_API_KEY missing')
    out=base/'gateway_runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True,exist_ok=False)
    system=system_identity([Path(__file__),root/'benchmark/nara_pilot_provider.py',root/'benchmark/verified_source_inputs.py',root/'benchmark/captured_inputs.py'])
    write_json(out/'system.json',system);source_snapshot=snapshot_system(system,out)
    config={'experiment':protocol['experiment'],'protocol':bind(base/'provider_pilot/protocol.json',root),'system':bind(out/'system.json',root),'system_snapshot':bind(source_snapshot,root),'conservative_usd_rates_per_million':rates,'billing_confirmed':False,'local_model_used':False}
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'));log=base/'experiments_log.json'
    common={'run_id':out.name,'seed':protocol['seed'],'config':config}
    claim_dispatch(permit_path,bind(approval_path,root),out.name,max_calls)
    append_experiment(log,split,dict(common,kind='dispatch-train',metrics=None,sample_ids=[]))
    guard=SpendGuard(root/'data/research/spend_ledger.json',limit_usd=10,pricing={MODEL:rates})
    budget_before=guard.report();COST_RATES[MODEL]=rates
    router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',spend_guard=guard,remote_model_ids={MODEL})
    pilot=NaraPilot(api_key=key,router=router,output_dir=out/'calls',max_calls=max_calls)
    observations=[];stop='';stream=io.StringIO()
    try:
        for identity in protocol['train_identities']:
            print('Starting real cloud-only TRAIN analysis',identity[:20],flush=True)
            inputs=load_train_inputs(root,identity,require_opcodes=True)
            with redirect_stdout(stream),no_network():
                result,sequence,info=inputs.orchestrator(out/'forensics').run(inputs.structured['transaction_hash'],'eth')
                if result is None:raise ValueError('Production Stage1 failed')
                ranking=FunctionRanker().rank(result,{'repeated_patterns':result.repeated_patterns,'function_call_loc_memo':result.function_call_loc_memo})
            downloader=VerifiedSourceDownloader.factory(root=root,evidence_binding=protocol['source_inputs'],train_identity=identity)
            analyzer=FunctionAnalyzer(model=MODEL,router=router,agent_factory=pilot.factory,contract_downloader_factory=downloader)
            with redirect_stdout(stream):output=analyzer.run(result,sequence,info,ranking)
            path=out/(identity.replace(':','-')+'.json');write_json(path,{'identity':identity,'production_output':output,'inputs':inputs.evidence,'source_scope':'All cached verified ABI functions; missing contract sources remain unavailable'})
            observations.append({'identity':identity,'complete':bool(output and output.get('analysis_complete')),'artifact':bind(path,root)})
    except StudyStop as error:stop=str(error)
    except BudgetApprovalRequired:stop='CUMULATIVE_BUDGET_DISPATCH_STOPPED'
    except Exception as error:stop='Production pilot failed: '+type(error).__name__
    finally:
        stdout=stream.getvalue()
        if key in stdout:stdout='Output withheld: credential echo detected'
        (out/'stdout.txt').write_bytes(stdout.encode('utf-8'))
        budget_after=guard.report()
        report={'run_id':out.name,'scope':'Real cloud-only TRAIN production function-analysis pilot; no native vendor/local/hybrid claim','config':config,'observations':observations,'stop_reason':stop or pilot.stop_reason,'completion_requests':pilot.calls,'complete_cases':sum(r['complete'] for r in observations),'requested_train_cases':2,'metrics':None,'metric_status':'UNSCORED: complete output and independent rank-schema validation required; no target labels entered prediction','budget_estimate_before_usd':budget_before['spent_usd'],'budget_estimate_after_usd':budget_after['spent_usd'],'incremental_conservative_estimate_usd':budget_after['spent_usd']-budget_before['spent_usd'],'billing_confirmed':False,'requested_model_identity':'Agnes 2.5 Flash (agnes-2.5-flash)','pilot_stop_reason':pilot.stop_reason,'approval':bind(approval_path,root),'ledger_records':[bind(p,root) for p in sorted((out/'calls/ledger').glob('*.json'))],'calls':[bind(p,root) for p in sorted((out/'calls').glob('*.json'))],'heldout_used':False,'final_exam_dispatched':False,'local_model_used':False}
        write_json(out/'summary.json',report)
        append_experiment(log,split,dict(common,kind='recorded-train-pilot',metrics=None,sample_ids=[],evidence=bind(out/'summary.json',root)))
        print(json.dumps({'run_id':out.name,'requests':pilot.calls,'complete_cases':report['complete_cases'],'stop_reason':report['stop_reason'],'cumulative_conservative_estimate_usd':budget_after['spent_usd']}),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--approval-file',type=Path);args=parser.parse_args();run(live=args.live,approval_file=args.approval_file)
