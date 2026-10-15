"""Execute real Stage 1 on independently acquired, narrow EOA controls."""
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from benchmark.research_protocol import read_bound,bind,write_json
from scripts.acquire_distinct_benign_controls import eligibility
from scripts.capture_authentic_traces import validate_call_identity
from scripts.run_train_production import no_network
from scripts.run_authentic_research import system_identity,snapshot_system
from benchmark.captured_inputs import _CapturedSequencer,_CapturedInfo
from faultseeker.utils.rpc_provider import normalize_trace_node
from faultseeker.forensics.orchestrator import ForensicsOrchestrator

def load_controls(root=ROOT):
    root=Path(root);base=root/'reports/cohort_rebuild_v2'
    summary=json.loads((base/'benign_controls/summary.json').read_text(encoding='utf-8'))
    prereg=json.loads(read_bound(summary['preregistration'],root))
    chain=json.loads(read_bound(summary['chain_evidence'],root))
    if chain['response'].get('result')!='0x1': raise ValueError('Control chain identity not verified')
    if summary['study']!=prereg['study'] or summary['accepted_count']!=len(summary['accepted']): raise ValueError('Control manifest count mismatch')
    hashes=set();senders=set();recipients=set();records=[]
    for admitted in summary['accepted']:
        record=json.loads(read_bound(admitted['record'],root))
        block=json.loads(read_bound(record['canonical']['block'],root))['response']['result']
        parent=json.loads(read_bound(record['canonical']['parent'],root))['response']['result']
        tx=record['transaction'];receipt=record['receipt']
        if block['parentHash']!=parent['hash'] or int(parent['number'],16)!=int(block['number'],16)-1: raise ValueError('Control parent block mismatch')
        if int(block['number'],16) not in prereg['block_numbers']: raise ValueError('Outside preregistered blocks')
        expected=[(tx['to'],parent['hash']),(tx['to'],block['hash']),(tx['from'],parent['hash'])]
        code_requests=[r for r in record['requests'] if r['request']['method']=='eth_getCode']
        if len(code_requests)!=3: raise ValueError('Missing control code records')
        codes=[]
        for request,(address,blockhash) in zip(code_requests,expected):
            if request['request']['params']!=[address,{'blockHash':blockhash,'requireCanonical':True}]: raise ValueError('Code query identity mismatch')
            codes.append(request.get('response',{}).get('result'))
        receipts=[r for r in record['requests'] if r['request']['method']=='eth_getTransactionReceipt']
        if len(receipts)!=1 or receipts[0]['request']['params']!=[tx['hash']] or receipts[0]['response']['result']!=receipt: raise ValueError('Receipt query mismatch')
        if eligibility(tx,block,receipt,codes,hashes,senders,recipients): raise ValueError('Control admission no longer valid')
        if admitted['transaction_hash']!=tx['hash'] or admitted['accepted'] is not True or record['accepted'] is not True: raise ValueError('Control accepted identity mismatch')
        hashes.add(tx['hash'].lower());senders.add(tx['from'].lower());recipients.add(tx['to'].lower())
        record['record_binding']=admitted['record'];records.append(record)
    return records

def observe_control(record,cache_dir,root=ROOT):
    tx=record['transaction'];receipt=record['receipt'];call=record.get('call_trace',{})
    if call.get('available') is not True: raise ValueError('Authenticated control call trace unavailable')
    trace=call['result'];validate_call_identity(trace,tx,receipt)
    if trace.get('input')!=tx['input'] or trace.get('value')!=tx['value'] or trace.get('calls'): raise ValueError('EOA trace mismatch')
    stream=io.StringIO();start=time.perf_counter()
    with no_network() as attempts,redirect_stdout(stream):
        structured={'transaction_hash':tx['hash'],'chain':'eth','trace':normalize_trace_node(trace),
            'storage_events':[],'storage_reads':[],'state_diff':{},'trace_coverage':{
                'trace_complete':True,'storage_trace_complete':False,'token_flow_complete':False,'multi_tx_context_complete':False}}
        orchestrator=ForensicsOrchestrator(cache_dir=str(cache_dir),txn_sequencer=_CapturedSequencer(structured),txn_info_collector=_CapturedInfo(tx,receipt,tx['hash'],'eth'))
        result,sequence,info=orchestrator.run(tx['hash'],'eth')
    if result is None or attempts[0]: raise RuntimeError('Control production analysis failed or attempted network')
    return {'transaction_hash':tx['hash'],'evidence':record['record_binding'],'verdict':result.rule_verdict,
        'confidence':result.rule_confidence,'matched_rule':result.matched_rule,'coverage':result.signals['coverage'],
        'signals':result.signals,'network_attempts':attempts[0],'stage2_executed':False,
        'duration_seconds':time.perf_counter()-start,'duration_scope':'Captured inputs and actual production Stage1 only; no inference latency',
        'benign_skip_eligible':result.rule_verdict=='BENIGN','stdout':stream.getvalue()}

def run(root=ROOT):
    root=Path(root);base=root/'reports/cohort_rebuild_v2';records=load_controls(root)
    out=base/'benign_control_runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True,exist_ok=False)
    system=system_identity([Path(__file__),root/'scripts/acquire_distinct_benign_controls.py',root/'benchmark/captured_inputs.py'])
    write_json(out/'system.json',system);snapshot=snapshot_system(system,out)
    observed=[];missing=[]
    for record in records:
        try:
            result=observe_control(record,out/'forensics',root);observed.append(result);write_json(out/(result['transaction_hash']+'.json'),result)
        except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
            missing.append({'transaction_hash':record['transaction']['hash'],'reason':str(error)[:200],'error_type':type(error).__name__})
    n=len(observed)
    report={'scope':'Preregistered distinct plain-transfer controls; production Stage1 only',
        'study':bind(base/'benign_controls/summary.json',root),'preregistration':bind(base/'benign_control_preregistration.json',root),
        'system':bind(out/'system.json',root),'source_snapshot':bind(snapshot,root),
        'admitted_count':len(records),'observed_count':n,'missing':missing,
        'verdict_counts':dict(Counter(r['verdict'] for r in observed)),
        'benign_skip_eligible_fraction':sum(r['benign_skip_eligible'] for r in observed)/n if n else None,
        'measured_stage1_seconds':sum(r['duration_seconds'] for r in observed),
        'observations':[bind(out/(r['transaction_hash']+'.json'),root) for r in observed],
        'unmeasured':['General benign smart-contract false-positive rate','Paired prefilter or billed inference savings','Full-system final held-out metrics'],
        'network_requests':0,'heldout_used':False,'final_exam_dispatched':False}
    write_json(out/'summary.json',report);print(json.dumps({'run':out.relative_to(root).as_posix(),'observed':n,'verdicts':report['verdict_counts'],'skip_eligible_fraction':report['benign_skip_eligible_fraction']},indent=2));return report

if __name__=='__main__':run()
