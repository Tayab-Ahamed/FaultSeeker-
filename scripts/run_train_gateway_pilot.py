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
from benchmark.pilot_token_guard import DailyTokenGuard,DailyTokenLimitReached
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
    if approval.get('mode')=='standing-train-daily-allowance':
        if (approval.get('approved') is not True or cap is not None
                or approval.get('protocol')!=protocol_binding
                or approval.get('destination')!='https://router.bynara.id/v1/chat/completions'
                or approval.get('model')!=MODEL
                or type(approval.get('daily_token_limit')) is not int
                or approval['daily_token_limit']!=7_000_000
                or any(approval.get(k) is not True for k in ('stop_on_any_error','train_only','labels_excluded','heldout_excluded','paper_env_excluded'))
                or 'max_incremental_estimated_usd' in approval):
            raise ValueError('Explicit standing TRAIN daily allowance scope missing or changed')
        return None
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


def approved_budget_limit(approval,budget_before):
    """Apply an optional approved batch ceiling to the existing shared ledger.

    This computes a conservative estimated-spend limit, not a billed-price claim.
    Pending reservations remain accounted for by SpendGuard before dispatch.
    """
    spent=budget_before.get('spent_usd')
    if type(spent) not in (int,float) or not math.isfinite(spent) or not 0<=spent<=10:
        raise ValueError('Invalid cumulative budget state')
    if 'max_incremental_estimated_usd' not in approval:return 10.0
    amount=approval['max_incremental_estimated_usd']
    if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<amount<=10:
        raise ValueError('Invalid approved incremental estimated-spend cap')
    return min(10.0,spent+amount)


def claim_dispatch(path,approval,run_id,max_calls=20):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle:
        json.dump({'run_id':run_id,'approval':approval,'max_completion_requests':max_calls},handle,indent=2)
        handle.flush();os.fsync(handle.fileno())


def import_historical_tokens(guard,root):
    """Import actual saved usage once; unknown dates/usage are conservative.

    Proposal records have no dispatch timestamp, so carry their allocations
    into the current UTC bucket rather than infer a free allowance. These
    inputs only initialize accounting and never enter any prediction prompt.
    """
    root=Path(root);base=root/BASE;day=guard.report()['bucket']
    for summary_path in sorted((base/'gateway_runs').glob('*/summary.json')):
        summary=json.loads(summary_path.read_text(encoding='utf-8'))
        run_day=datetime.strptime(summary['run_id'][:8],'%Y%m%d').date().isoformat()
        for binding in summary.get('calls',[]):
            record=json.loads(read_bound(binding,root))
            if record.get('requested_alias')!=MODEL:continue
            if record.get('daily_token_accounting') or record.get('daily_token_reservation_id'):
                accounting=record.get('daily_token_accounting') or {'reservation_id':record['daily_token_reservation_id']}
                settled=[e for e in guard.report()['events'] if e.get('event')=='settle'
                         and e.get('id')==accounting['reservation_id']]
                if len(settled)!=1 or ('charged_tokens' in accounting and settled[0]['tokens']!=accounting['charged_tokens']):
                    raise ValueError('Existing daily token settlement is missing or inconsistent')
                continue
            usage=record.get('usage') or {}
            if type(usage.get('prompt_tokens')) is int and type(usage.get('completion_tokens')) is int:
                guard.import_usage_once(binding['path'],run_day,usage['prompt_tokens'],usage['completion_tokens'],binding)
            else:
                bound=2*record['request_bytes']+1024+4096
                guard.import_allocation_once(binding['path'],run_day,bound,binding)
    for path in sorted((base/'proposals').glob('batch_*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('model')!=MODEL:continue
        binding=bind(path,root);source='undated-proposal:'+binding['path']
        # Preserve original accounting day on later runs; never import twice.
        existing=guard.report()['imports'].get(source)
        bucket=existing['bucket'] if existing else day
        usage=(record.get('response') or {}).get('usage') or {}
        if type(usage.get('prompt_tokens')) is int and type(usage.get('completion_tokens')) is int:
            guard.import_usage_once(source,bucket,usage['prompt_tokens'],usage['completion_tokens'],binding)
        else:
            payload=record['request'];bound=2*len(json.dumps(payload,ensure_ascii=False).encode('utf-8'))+1024+payload['max_tokens']
            guard.import_allocation_once(source,bucket,bound,binding)

def select_train_identities(protocol, requested_ids=None):
    """Select only an explicit nonempty unique subset of preregistered TRAIN."""
    available = protocol['train_identities']
    selected = list(available) if requested_ids is None else requested_ids
    if (not isinstance(selected, (list, tuple)) or not selected
            or any(not isinstance(key, str) for key in selected)
            or len(set(selected)) != len(selected)
            or not set(selected) <= set(available)):
        raise ValueError('TRAIN identity selector requires a nonempty unique protocol subset')
    return list(selected)


def run(root=ROOT,live=False,approval_file=None,requested_ids=None):
    if not live:raise ValueError('Explicit --live required before credentials or dispatch')
    root=Path(root);base=root/BASE;protocol,rates=configuration(root)
    selected_identities=select_train_identities(protocol,requested_ids)
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
    standing=approval.get('mode')=='standing-train-daily-allowance'
    if permit_path.exists() and not standing:raise ValueError('Approved dispatch permit already consumed')
    guard=SpendGuard(root/'data/research/spend_ledger.json',limit_usd=10,pricing={MODEL:rates})
    budget_before=guard.report()
    guard.limit_usd=approved_budget_limit(approval,budget_before)
    daily_guard=None
    if standing:
        daily_guard=DailyTokenGuard(root/'data/research/nara_daily_tokens.json')
        import_historical_tokens(daily_guard,root)
    daily_before=daily_guard.report() if daily_guard else None
    from dotenv import dotenv_values
    values={}
    for path in (Path(r'C:\Users\91701\Downloads\Wingman-main\Wingman-main\.env'),root/'.env'):
        if path.exists():values.update({k:v for k,v in dotenv_values(path).items() if v})
    key=values.get('BYNARA_API_KEY')
    if not key:raise ValueError('BYNARA_API_KEY missing')
    out=base/'gateway_runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True,exist_ok=False)
    if standing:
        permit_path=out/'dispatch_permit.json'
    system=system_identity([Path(__file__),root/'benchmark/nara_pilot_provider.py',root/'benchmark/nara_http_transport.py',root/'benchmark/pilot_token_guard.py',root/'benchmark/verified_source_inputs.py',root/'benchmark/execution_source_inputs.py',root/'benchmark/captured_inputs.py'])
    write_json(out/'system.json',system);source_snapshot=snapshot_system(system,out)
    config={'experiment':protocol['experiment'],'protocol':bind(base/'provider_pilot/protocol.json',root),'system':bind(out/'system.json',root),'system_snapshot':bind(source_snapshot,root),'conservative_usd_rates_per_million':rates,'billing_confirmed':False,'local_model_used':False,'incremental_estimated_usd_cap':approval.get('max_incremental_estimated_usd'),'cumulative_dispatch_limit_usd':guard.limit_usd,'requested_train_identities':selected_identities,'requested_train_cases':len(selected_identities)}
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'));log=base/'experiments_log.json'
    common={'run_id':out.name,'seed':protocol['seed'],'config':config}
    claim_dispatch(permit_path,bind(approval_path,root),out.name,max_calls)
    append_experiment(log,split,dict(common,kind='dispatch-train',metrics=None,sample_ids=[]))
    COST_RATES[MODEL]=rates
    router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',spend_guard=guard,remote_model_ids={MODEL})
    pilot=NaraPilot(api_key=key,router=router,output_dir=out/'calls',max_calls=max_calls,daily_token_guard=daily_guard,
                    transport_timeout=300 if standing else 60)
    observations=[];stop='';stream=io.StringIO()
    try:
        for identity in selected_identities:
            print('Starting real cloud-only TRAIN analysis',identity[:20],flush=True)
            inputs=load_train_inputs(root,identity,require_opcodes=True)
            with redirect_stdout(stream),no_network():
                result,sequence,info=inputs.orchestrator(out/'forensics').run(inputs.structured['transaction_hash'],'eth')
                if result is None:raise ValueError('Production Stage1 failed')
                ranking=FunctionRanker().rank(result,{'repeated_patterns':result.repeated_patterns,'function_call_loc_memo':result.function_call_loc_memo})
            downloader=VerifiedSourceDownloader.factory(root=root,evidence_binding=protocol['source_inputs'],train_identity=identity,include_execution_spans=True)
            analyzer=FunctionAnalyzer(model=MODEL,router=router,agent_factory=pilot.factory,contract_downloader_factory=downloader,analysis_error_handler=pilot.stop_after_analysis_error)
            with redirect_stdout(stream):output=analyzer.run(result,sequence,info,ranking)
            path=out/(identity.replace(':','-')+'.json');write_json(path,{'identity':identity,'production_output':output,'inputs':inputs.evidence,'source_scope':'All cached verified ABI functions; missing contract sources remain unavailable'})
            observations.append({'identity':identity,'complete':bool(output and output.get('analysis_complete')),'artifact':bind(path,root)})
    except StudyStop as error:stop=str(error)
    except BudgetApprovalRequired:stop='CUMULATIVE_BUDGET_DISPATCH_STOPPED'
    except DailyTokenLimitReached:stop='DAILY_TOKEN_DISPATCH_STOPPED'
    except Exception as error:stop='Production pilot failed: '+type(error).__name__
    finally:
        stdout=stream.getvalue()
        if key in stdout:stdout='Output withheld: credential echo detected'
        (out/'stdout.txt').write_bytes(stdout.encode('utf-8'))
        budget_after=guard.report()
        report={'run_id':out.name,'scope':'Real cloud-only TRAIN production function-analysis pilot; no native vendor/local/hybrid claim','config':config,'observations':observations,'stop_reason':stop or pilot.stop_reason,'completion_requests':pilot.calls,'complete_cases':sum(r['complete'] for r in observations),'requested_train_cases':len(selected_identities),'requested_train_identities':selected_identities,'metrics':None,'metric_status':'UNSCORED: complete output and independent rank-schema validation required; no target labels entered prediction','budget_estimate_before_usd':budget_before['spent_usd'],'budget_estimate_after_usd':budget_after['spent_usd'],'incremental_conservative_estimate_usd':budget_after['spent_usd']-budget_before['spent_usd'],'billing_confirmed':False,'requested_model_identity':'Agnes 2.5 Flash (agnes-2.5-flash)','pilot_stop_reason':pilot.stop_reason,'approval':bind(approval_path,root),'ledger_records':[bind(p,root) for p in sorted((out/'calls/ledger').glob('*.json'))],'calls':[bind(p,root) for p in sorted((out/'calls').glob('*.json'))],'heldout_used':False,'final_exam_dispatched':False,'local_model_used':False}
        report['standing_allowance']={'enabled':standing,'request_cap':max_calls,'daily_token_limit':7_000_000 if standing else None,
            'time_zone':'UTC' if standing else None,'before':{k:daily_before[k] for k in ('bucket','used','reserved','remaining')} if daily_before else None,
            'after':{k:daily_guard.report()[k] for k in ('bucket','used','reserved','remaining')} if daily_guard else None}
        write_json(out/'summary.json',report)
        append_experiment(log,split,dict(common,kind='recorded-train-pilot',metrics=None,sample_ids=[],evidence=bind(out/'summary.json',root)))
        print(json.dumps({'run_id':out.name,'requests':pilot.calls,'complete_cases':report['complete_cases'],'stop_reason':report['stop_reason'],'cumulative_conservative_estimate_usd':budget_after['spent_usd']}),flush=True)
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--approval-file',type=Path)
    parser.add_argument('--identity',action='append',help='Nonempty unique subset of existing protocol TRAIN identities')
    args=parser.parse_args(argv)
    return run(live=args.live,approval_file=args.approval_file,requested_ids=args.identity)


if __name__=='__main__':
    main()
