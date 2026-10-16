"""Offline diagnostic replay of hash-bound real TRAIN gateway HTTP observations.

This is a current-code reproduction prefix, not new inference, new measurements,
or an empirical quality experiment. Tape mismatches stop before response return.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from benchmark.research_protocol import bind,read_bound,sha,write_json,load_train
from benchmark.nara_pilot_provider import NaraPilot,StudyStop,MODEL,ENDPOINT
from benchmark.verified_source_inputs import VerifiedSourceDownloader
from benchmark.captured_inputs import load_train_inputs
from faultseeker.core.spend_guard import SpendGuard
from faultseeker.core.llm_router import HybridLLMRouter,COST_RATES
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.function_analysis.function_ranker import FunctionRanker
from scripts.run_train_production import no_network
from scripts.run_authentic_research import system_identity,snapshot_system

DEFAULT_SUMMARY='reports/cohort_rebuild_v2/gateway_runs/20261015T180644-7cc259e6/summary.json'
DEFAULT_SUMMARY_SHA='1e496e3cd7c063594b1cbab4a9f80992eccd3bf40bc588cb80793f9db60b4b4c'


class ReplayBoundary(StudyStop):
    """Exact tape boundary bypasses broad production Exception recovery."""


class StrictTape:
    def __init__(self,bindings,root):
        self.bindings=list(bindings);self.root=Path(root);self.matched=0;self.failure=None
    def stop(self,reason,**details):
        self.failure={'reason':reason,'call_number':self.matched+1,**details}
        raise ReplayBoundary(reason)
    def __call__(self,url,headers,body,timeout):
        if self.matched>=len(self.bindings):self.stop('TAPE_EXHAUSTED')
        binding=self.bindings[self.matched]
        try:record=json.loads(read_bound(binding,self.root))
        except (ValueError,OSError,KeyError,TypeError):self.stop('HISTORICAL_CALL_BINDING_INVALID')
        if url!=ENDPOINT or record.get('endpoint')!=ENDPOINT:self.stop('ENDPOINT_MISMATCH')
        if record.get('requested_alias')!=MODEL or record.get('request',{}).get('model')!=MODEL:
            self.stop('REQUEST_MODEL_MISMATCH')
        try:actual=json.loads(body.decode('utf-8'))
        except (UnicodeError,ValueError,AttributeError):self.stop('REQUEST_NOT_JSON')
        actual_sha=sha(body)
        if actual_sha!=record.get('request_sha256'):
            self.stop('REQUEST_BYTES_DIVERGED',actual_request_sha256=actual_sha,recorded_request_sha256=record.get('request_sha256'))
        if actual!=record.get('request'):self.stop('REQUEST_JSON_DIVERGED')
        if len(body)!=record.get('request_bytes'):self.stop('REQUEST_LENGTH_MISMATCH')
        if record.get('call_number')!=self.matched+1:self.stop('HISTORICAL_CALL_ORDER_MISMATCH')
        if type(record.get('http_status')) is not int or not 100<=record['http_status']<=599:
            self.stop('HTTP_STATUS_INVALID')
        if not isinstance(record.get('response_text'),str):self.stop('RESPONSE_TEXT_MISSING')
        raw=record['response_text'].encode('utf-8')
        if sha(raw)!=record.get('response_sha256') or len(raw)!=record.get('response_bytes'):
            self.stop('RESPONSE_BYTES_INVALID')
        try:response=json.loads(raw)
        except ValueError:self.stop('RESPONSE_NOT_JSON')
        if response!=record.get('response'):self.stop('RESPONSE_JSON_DIVERGED')
        if response.get('model')!=MODEL or record.get('returned_alias')!=MODEL:
            self.stop('RESPONSE_MODEL_MISMATCH')
        self.matched+=1
        return record['http_status'],raw,ENDPOINT


class ReplayClock:
    def __init__(self):self.now=0.0
    def clock(self):return self.now
    def sleep(self,seconds):self.now+=max(0,float(seconds))


def run(root=ROOT,summary_binding=None,output=None):
    root=Path(root).resolve()
    historical=summary_binding or {'path':DEFAULT_SUMMARY,'sha256':DEFAULT_SUMMARY_SHA}
    summary=json.loads(read_bound(historical,root))
    if summary.get('heldout_used') is not False or not 1<=summary.get('completion_requests',0)<=20:
        raise ValueError('Historical TRAIN-only bounded gateway run required')
    if len(summary['calls'])!=summary['completion_requests']:raise ValueError('Historical tape count mismatch')
    protocol_binding=summary['config']['protocol'];protocol=json.loads(read_bound(protocol_binding,root))
    read_bound(protocol['source_inputs'],root)
    split=json.loads((root/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    train={r['chain']+':'+r['txn_hash'] for r in load_train(split,root)}
    if not set(protocol['train_identities'])<=train:raise ValueError('Historical protocol contains non-TRAIN identity')
    rates=summary['config']['conservative_usd_rates_per_million']
    if set(rates)!={'input','output'} or any(type(v) not in (int,float) or not 0<v<1000000 for v in rates.values()):
        raise ValueError('Historical simulation pricing invalid')
    tape=StrictTape(summary['calls'],root)
    # Validate every referenced immutable record before production execution.
    for binding in summary['calls']:read_bound(binding,root)
    for key in ('system','system_snapshot'):read_bound(summary['config'][key],root)
    ledger=root/'data/research/spend_ledger.json'
    real_ledger_before=ledger.read_bytes()
    out=Path(output) if output else root/'reports/cohort_rebuild_v2/gateway_prefix_replay'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    out.mkdir(parents=True,exist_ok=False)
    system=system_identity([Path(__file__),root/'benchmark/nara_pilot_provider.py',root/'benchmark/verified_source_inputs.py',root/'benchmark/execution_source_inputs.py',root/'benchmark/captured_inputs.py'])
    write_json(out/'system.json',system);snapshot=snapshot_system(system,out)
    previous_rate=COST_RATES.get(MODEL);had_rate=MODEL in COST_RATES
    previous_ledger=os.environ.get('FAULTSEEKER_SPEND_LEDGER')
    observations=[];stop=None;error_type=None;stream=io.StringIO();attempts=[0];simulation=None
    try:
        with tempfile.TemporaryDirectory(prefix='faultseeker-gateway-prefix-') as temp:
            isolated=Path(temp)/'simulation-ledger.json'
            os.environ['FAULTSEEKER_SPEND_LEDGER']=str(isolated)
            guard=SpendGuard(isolated,limit_usd=10,pricing={MODEL:rates})
            COST_RATES[MODEL]=rates
            router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',spend_guard=guard,remote_model_ids={MODEL})
            clock=ReplayClock()
            pilot=NaraPilot(api_key='offline-replay-nonsecret-placeholder',router=router,output_dir=out/'simulated_calls',
                transport=tape,clock=clock.clock,sleep=clock.sleep,max_calls=20)
            try:
                with redirect_stdout(stream),no_network() as attempts:
                    for identity in protocol['train_identities']:
                        inputs=load_train_inputs(root,identity,require_opcodes=True)
                        stage_one,sequence,info=inputs.orchestrator(out/'forensics').run(inputs.structured['transaction_hash'],'eth')
                        if stage_one is None:raise ValueError('Recorded production Stage1 unavailable')
                        ranking=FunctionRanker().rank(stage_one,{'repeated_patterns':stage_one.repeated_patterns,'function_call_loc_memo':stage_one.function_call_loc_memo})
                        downloader=VerifiedSourceDownloader.factory(root=root,evidence_binding=protocol['source_inputs'],train_identity=identity,include_execution_spans=True)
                        analyzer=FunctionAnalyzer(model=MODEL,router=router,agent_factory=pilot.factory,contract_downloader_factory=downloader,analysis_error_handler=pilot.stop_after_analysis_error)
                        production=analyzer.run(stage_one,sequence,info,ranking)
                        path=out/(identity.replace(':','-')+'.json');write_json(path,{'identity':identity,'production_output':production,'inputs':inputs.evidence,'diagnostic_only':True})
                        observations.append({'identity':identity,'artifact':bind(path,root)})
            except ReplayBoundary as error:stop=str(error)
            except StudyStop:stop='NARA_STUDY_BOUNDARY'
            except Exception as error:stop='PRODUCTION_ERROR';error_type=type(error).__name__
            finally:simulation=guard.report()
    finally:
        if had_rate:COST_RATES[MODEL]=previous_rate
        else:COST_RATES.pop(MODEL,None)
        if previous_ledger is None:os.environ.pop('FAULTSEEKER_SPEND_LEDGER',None)
        else:os.environ['FAULTSEEKER_SPEND_LEDGER']=previous_ledger
        after=ledger.read_bytes();unchanged=after==real_ledger_before
        (out/'stdout.txt').write_bytes(stream.getvalue().encode('utf-8'))
        write_json(out/'simulated_accounting.json',{'scope':'Replay-only synthetic accounting of historical usage; no new provider billing','temporary_ledger_deleted':True,'simulation':simulation})
        report={'scope':'Current-code exact HTTP-observation prefix replay for debugging only; not a new empirical quality experiment',
            'historical_summary':historical,'historical_calls':summary['calls'],'protocol':protocol_binding,'source_inputs':protocol['source_inputs'],
            'historical_system':summary['config']['system'],'historical_system_snapshot':summary['config']['system_snapshot'],
            'current_system':bind(out/'system.json',root),'current_source_snapshot':bind(snapshot,root),
            'matched_prefix':tape.matched,'historical_observations':len(summary['calls']),'stop_reason':stop or 'PRODUCTION_RETURNED',
            'timing_reproduced':False,'timing_limitation':'Only provider spacing uses a replay clock; production wall-time budgets and runtimes are not reproduced. Conclusions are limited to exact matched request prefix.',
            'boundary':tape.failure,'error_type':error_type,'observations':observations,'metrics':None,
            'new_inference_requests':0,'new_rpc_requests':0,'network_attempts':attempts[0],'heldout_used':False,
            'real_spend_ledger_unchanged':unchanged,'real_ledger_sha256_before':sha(real_ledger_before),'real_ledger_sha256_after':sha(after),
            'accounting':bind(out/'simulated_accounting.json',root),'simulated_calls':[bind(p,root) for p in sorted((out/'simulated_calls').glob('call-*.json'))]}
        write_json(out/'summary.json',report)
        if not unchanged:raise ValueError('Real spend ledger changed during offline diagnostic')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary');parser.add_argument('--summary-sha256');args=parser.parse_args()
    if bool(args.summary)!=bool(args.summary_sha256):parser.error('Both --summary and --summary-sha256 are required together')
    report=run(summary_binding={'path':args.summary,'sha256':args.summary_sha256} if args.summary else None)
    print(json.dumps({key:report[key] for key in ('matched_prefix','stop_reason','new_inference_requests','network_attempts','real_spend_ledger_unchanged')}))
