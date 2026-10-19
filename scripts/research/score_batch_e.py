"""Predict frozen Batch E without labels, then acquire a permanent one-score lock."""
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
import hashlib,io,json,pickle,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.research import selected_address_localizer as localizer
import batchC_phase2 as adapters
from faultseeker.utils.rpc_provider import normalize_trace_node
from faultseeker.function_analysis.function_ranker import FunctionRanker
from faultseeker.forensics.orchestrator import ForensicsOrchestrator
from fresh_evaluation_safety import acquire_score_lock,verify_frozen_inputs
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/new_batches/batchE'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')

class DecodedSequencer(adapters._CapturedSequencer):
    def __init__(self,structured,names):super().__init__(structured);self.names=names
    def run(self,tx,chain):
        result=super().run(tx,chain)
        def label(node):
            literal=str(node.get('function') or '')
            node['runtime_selector']=literal
            name=self.names.get(literal.lower(),{}).get('decoded_name','')
            if name:node['function']=name
            for child in node.get('children') or []:label(child)
        label(result['trace'])
        result['address_calls']={a:[self.names.get(str(s).lower(),{}).get('decoded_name') or s for s in values] for a,values in result['address_calls'].items()}
        return result


def runtime_inputs(raw,names):
    structured={'transaction_hash':raw['transaction_hash'],'chain':'eth','trace':normalize_trace_node(raw['trace']),'storage_events':[],'storage_reads':[],'state_diff':{},'trace_coverage':{'trace_complete':True,'storage_trace_complete':False,'token_flow_complete':False,'multi_tx_context_complete':False}}
    sequencer=DecodedSequencer(structured,names)
    orchestrator=ForensicsOrchestrator(model='llm-free-function-ranker',txn_sequencer=sequencer,txn_info_collector=adapters._CapturedInfo(raw['transaction'],raw['receipt'],raw['transaction_hash']))
    with redirect_stdout(io.StringIO()):
        result,_,_=orchestrator.run(raw['transaction_hash'],'eth')
        predictions=[dict(p) for p in FunctionRanker().rank(result,{'repeated_patterns':result.repeated_patterns,'function_call_loc_memo':result.function_call_loc_memo}).ranked_functions]
    def render(node,depth=0):
        literal=str(node.get('input') or '')[:10].lower();name=names.get(literal,{}).get('decoded_name') or literal or 'fallback'
        address=str(node.get('to') or '').lower();kind=str(node.get('type') or 'CALL').lower()
        lines=['    '*depth+('â””â”€ ' if depth else '')+f'[0] {address}::{name}() [{kind}]'] if address else []
        for child in node.get('calls') or []:lines.extend(render(child,depth+1))
        return lines
    return predictions,'\n'.join(render(raw['trace']))


def inference_guard(event,args):
    if event in {'socket.connect','socket.getaddrinfo','http.client.connect','subprocess.Popen'}:
        raise RuntimeError('Network or subprocess forbidden during frozen inference')

def main():
    if (OUT/'score_started.lock').exists() or (OUT/'scoring.json').exists():raise RuntimeError('Batch E scoring already claimed')
    manifest=json.loads((ROOT/'reports/localization_continuous/merge/deployment_manifest.json').read_text())
    model=ROOT/manifest['model_path']
    if sha(model)!=manifest['model_sha256']:raise RuntimeError('Frozen model changed')
    for p,digest in manifest['code_sha256'].items():
        if sha(Path(p))!=digest:raise RuntimeError('Frozen ranker dependency changed')
    run=OUT/'capture_network_retry1';verified=json.loads((run/'verification.json').read_text());registry=json.loads((OUT/'registry/summary.json').read_text())
    if verified['status']!='COLLECTED_40_UNSCORED' or registry['status']!='COMPLETE_UNSCORED':raise RuntimeError('Acquisition incomplete; scoring forbidden')
    frozen=json.loads((OUT/'freeze.json').read_text())
    expected={OUT/'cohort.json':frozen['cohort_sha256'],model:manifest['model_sha256']}
    for row in verified['rows']:expected[ROOT/row['raw_path']]=row['raw_sha256']
    # Runtime code is frozen before any predictions. These are literal source hashes.
    runtime_files=list((ROOT/'faultseeker').rglob('*.py'))+[Path(__file__),Path(localizer.__file__),Path(adapters.__file__),ROOT/'scripts/research/response_bound_decoder.py',ROOT/'scripts/research/fresh_evaluation_safety.py',OUT/'registry/summary.json',run/'verification.json']
    for p in runtime_files:expected[p]=sha(p)
    code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    runtime_freeze={'git_commit':code_commit,'input_sha256':{str(p):digest for p,digest in expected.items()},'prediction_runs':0,'scoring_runs':0}
    with (OUT/'runtime_freeze.json').open('x',encoding='utf-8') as handle:json.dump(runtime_freeze,handle,indent=2)
    sys.addaudithook(inference_guard)
    # Our own locally produced pickle only, verified above before deserialization.
    bundle=pickle.loads(model.read_bytes())
    predictions=[];pred_dir=OUT/'predictions';pred_dir.mkdir(exist_ok=False)
    for row in verified['rows']:
        if not row['verified']:continue
        raw=json.loads((ROOT/row['raw_path']).read_text())
        observed,trace_text=runtime_inputs(raw,registry['mapping'])
        prepared=localizer.prepare(observed,trace_text)
        ranked=localizer.predict(bundle,prepared)
        artifact={'transaction_hash':row['transaction_hash'],'address_ranking':ranked,'observed_function_candidates':observed,'generic_decoding_not_verified_abi':True}
        path=pred_dir/(row['transaction_hash']+'.json');write(path,artifact)
        predictions.append(artifact)
        print(json.dumps({'predictions_completed':len(predictions),'scoring_runs':0}),flush=True)
    if len(predictions)!=40:raise RuntimeError('Wrong verified prediction population')
    verify_frozen_inputs(expected)
    acquire_score_lock(OUT/'score_started.lock',expected)
    # First access to target labels in this scorer occurs only after all predictions.
    labels={r['transaction_hash']:r['target_address'] for r in json.loads((OUT/'cohort.json').read_text())['rows']}
    scored=[]
    for row in predictions:
        rank=next((i for i,a in enumerate(row['address_ranking'],1) if a==labels[row['transaction_hash']]),None)
        scored.append({'transaction_hash':row['transaction_hash'],'address_rank':rank})
    ranks=[r['address_rank'] for r in scored]
    result={'status':'SCORED_ONCE','scoring_runs':1,'n':40,'endpoint':'address_only_PoC_target','metrics':localizer.margin.learner.base.metrics(ranks),'rows':scored,'model_sha256':manifest['model_sha256'],'runtime_commit':code_commit,'cohort_sha256':frozen['cohort_sha256'],'exact_function_metrics':None,'decoder_distribution_shift':True,'rpc_requests':verified['request_count']+1,'initial_sandbox_dns_dispatches':1,'registry_requests':registry['request_count'],'rate_limit_hits':verified['rate_limit_hits']+registry['rate_limit_hits'],'paid_spend_estimate_usd':0}
    write(OUT/'scoring.json',result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
