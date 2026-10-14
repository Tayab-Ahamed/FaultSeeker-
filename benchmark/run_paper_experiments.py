"""Run real paired paper experiments; missing evidence is a hard gate."""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.evidence_manifest import audit_dataset, _artifact, digest_file
from benchmark.detector_experiments import detector_observation, category_observation
from benchmark.paper_experiments import run_paired, compare_runs, summarize_categories, PipelineObservationAdapter


def execute(args):
    root = (args.evidence_root or args.cohort.parent).resolve()
    main_cohort = args.experiment in {'detectors','categories'}
    audit = audit_dataset(args.cohort, root, target=246 if main_cohort else 1)
    if (not audit['input_rows'] or audit['accepted_rows'] != audit['input_rows']
            or (main_cohort and audit['accepted_rows'] != 246)):
        return {'status':'BLOCKED-BY-DATA', 'audit':audit}, 2
    payload = json.loads(args.cohort.read_text(encoding='utf-8-sig'))
    records = payload['records'] if isinstance(payload,dict) else payload
    if args.experiment in {'detectors','categories'}:
        if args.experiment == 'categories':
            rows = []
            for record in records:
                capture = json.loads(_artifact(root,record['trace']).read_text(encoding='utf-8-sig'))
                receipt = json.loads(_artifact(root,record['receipt']).read_text(encoding='utf-8-sig'))
                rows.append(category_observation(capture,receipt,record['vulnerability_class']))
            return {'status':'MEASURED','categories':summarize_categories(rows)}, 0
        for record in records:
            if type(record.get('reentrancy_label')) is not bool:
                raise ValueError('BLOCKED-BY-DATA: adjudicated reentrancy_label is required')
            record['label'] = record['reentrancy_label']
        def analyze(record,variant,guidance):
            capture = json.loads(_artifact(root,record['trace']).read_text(encoding='utf-8-sig'))
            return detector_observation(capture,variant)
        runs = run_paired(records,analyze,['full','structural','repeated'])
        return {'status':'MEASURED','scope':'captured detector execution', 'runs':runs,
                'comparisons':{variant:compare_runs(runs[variant],runs['full']) for variant in ('structural','repeated')}}, 0
    if not args.execute_live:
        return {'status':'PENDING-CREDENTIALS','required_env':['DRPC_RPC_URL','DRPC_API_KEY','OLLAMA_HOST',
            'OPENAI_API_KEY','ETHERSCAN_API_KEY'],
            'required_options':['--execute-live','--pricing-file (for cloud calls)'],
            'note':'No model or RPC request was dispatched.'}, 2
    if not os.getenv('DRPC_RPC_URL'):
        return {'status':'PENDING-CREDENTIALS','required_env':['DRPC_RPC_URL','DRPC_API_KEY']}, 2
    if not args.pricing_file:
        raise ValueError('A sourced dated USD pricing snapshot is required before paid experiments')
    pricing = json.loads(args.pricing_file.read_text(encoding='utf-8-sig'))
    if (pricing.get('units') != 'USD per 1000000 tokens' or not pricing.get('verified_at')
            or not pricing.get('source_url') or args.cloud_model not in pricing.get('models',{})):
        raise ValueError('Pricing snapshot requires source, date, units and selected model')
    from faultseeker.core.llm_router import COST_RATES
    from faultseeker.core.config import FaultSeekerConfig
    from faultseeker.core.pipeline import FaultSeekerPipeline
    for model, rates in pricing['models'].items():
        if any(type(rates.get(key)) not in (int,float) or rates[key] <= 0 for key in ('input','output')):
            raise ValueError('Positive finite input/output prices required')
        import math
        if not all(math.isfinite(rates[key]) for key in ('input','output')):
            raise ValueError('Positive finite input/output prices required')
        COST_RATES[model] = rates
    variants = {'routing':['cloud_only','hybrid'], 'prefilter':['prefilter_off','prefilter_on'],
                'guidance':['unassisted','guided']}[args.experiment]
    if not args.selection_file:
        raise ValueError('BLOCKED-BY-DATA: preregistered selection file required')
    selection = json.loads(args.selection_file.read_text(encoding='utf-8-sig'))
    count = 20 if args.experiment=='guidance' else 100 if args.experiment=='routing' else selection.get('expected_n')
    if type(count) is not int or count<=0:
        raise ValueError('BLOCKED-BY-DATA: preregistered positive expected_n is required for the benign study')
    selected_ids = selection['transaction_ids']
    if len(selected_ids) != count or len(set(selected_ids)) != count:
        raise ValueError(f'BLOCKED-BY-DATA: exactly {count} unique preregistered transaction IDs required')
    indexed = {r['chain']+':'+r['txn_hash'].lower():r for r in records}
    records = [indexed[key] for key in selected_ids]
    for record in records:
        ground_truth = json.loads(_artifact(root,record['ground_truth']).read_text(encoding='utf-8-sig'))
        findings = ground_truth.get('findings')
        if not isinstance(findings,list) or any(not isinstance(item,dict) or
                not item.get('address') or not item.get('function') for item in findings):
            raise ValueError('BLOCKED-BY-DATA: ground truth findings need exact address and function signature')
        record['expected_functions'] = findings
        if type(record.get('label')) is not bool:
            raise ValueError('BLOCKED-BY-DATA: adjudicated binary exploit label required')
    if args.experiment=='prefilter' and any(record['label'] for record in records):
        raise ValueError('BLOCKED-BY-DATA: benign prefilter study requires independently benign labels')
    if args.experiment == 'routing' and Counter(r.get('workload_tier') for r in records) != Counter({1:50,2:30,3:20}):
        raise ValueError('BLOCKED-BY-DATA: 100-transaction workload must have recorded 50/30/20 tiers')
    def factory(variant):
        return FaultSeekerPipeline(FaultSeekerConfig(auto_route=True,track_cost=True,
            cloud_model=args.cloud_model,function_analysis_model=args.cloud_model,
            local_model=args.local_model,routing_strategy='cloud-only' if variant=='cloud_only' else 'hybrid',
            enable_benign_prefilter=variant != 'prefilter_off'))
    guidance = {}
    if args.experiment == 'guidance':
        policy = selection.get('simulated_guidance')
        if not isinstance(policy,dict) or not selection.get('simulation_policy'):
            raise ValueError('BLOCKED-BY-DATA: preregistered simulation policy and guidance required')
        guidance['guided'] = lambda row: policy[row['chain']+':'+row['txn_hash'].lower()]
    runs = run_paired(records, PipelineObservationAdapter(factory), variants,guidance)
    return {'status':'MEASURED','scope':'executed production pipeline; guidance is simulated',
            'pricing_sha256':digest_file(args.pricing_file), 'selection_sha256':digest_file(args.selection_file),
            'runs':runs,'comparison':compare_runs(runs[variants[0]],runs[variants[1]]),
            'benign_prefilter_fraction':{variant:sum(row['stage2_bypassed'] and not row['label'] for row in rows)/sum(not row['label'] for row in rows)
                if any(not row['label'] for row in rows) else None for variant,rows in runs.items()},
            'actual_query_tiers':{v:dict(Counter(call['tier'] for row in rows for call in row['query_records'])) for v,rows in runs.items()}}, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',type=Path,required=True)
    parser.add_argument('--evidence-root',type=Path)
    parser.add_argument('--experiment',choices=['detectors','categories','routing','prefilter','guidance'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute-live',action='store_true')
    parser.add_argument('--pricing-file',type=Path)
    parser.add_argument('--selection-file',type=Path)
    parser.add_argument('--cloud-model',default='gpt-4o-mini')
    parser.add_argument('--local-model',default='llama3:8b')
    args = parser.parse_args(argv)
    try:
        report, code = execute(args)
    except (KeyError,TypeError,ValueError,RuntimeError,OSError) as error:
        blocked = isinstance(error,KeyError) or str(error).startswith('BLOCKED-BY-DATA')
        report,code = {'status':'BLOCKED-BY-DATA' if blocked else 'FAILED',
                       'error_type':type(error).__name__,'reason':str(error)},2 if blocked else 1
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"{report['status']}: {args.output}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())
