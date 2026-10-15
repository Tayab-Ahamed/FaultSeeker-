"""Paired measurements from pipeline observations, with explicit denominators.

No outcome is inferred from a transaction hash or an attack label. Callers must
provide executed observations; fixtures prove plumbing, never paper statistics.
"""
import math
import time
from collections import defaultdict


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')
    return value


def confusion_metrics(labels, predictions):
    labels, predictions = list(labels), list(predictions)
    if not labels or len(labels) != len(predictions):
        raise ValueError('equal nonempty labels and predictions required')
    if any(type(v) is not bool for v in labels + predictions):
        raise ValueError('binary boolean labels and predictions required')
    tp = sum(y and p for y, p in zip(labels, predictions))
    fp = sum(not y and p for y, p in zip(labels, predictions))
    fn = sum(y and not p for y, p in zip(labels, predictions))
    tn = sum(not y and not p for y, p in zip(labels, predictions))
    return {'n': len(labels), 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': tp/(tp+fp) if tp+fp else None,
            'recall': tp/(tp+fn) if tp+fn else None,
            'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            'accuracy': (tp+tn)/len(labels)}


def run_paired(records, analyze, variants, guidance=None):
    records, variants = list(records), list(variants)
    if not records or not variants or len(set(variants)) != len(variants):
        raise ValueError('unique variants and nonempty records required')
    guidance = guidance or {}
    output = {variant: [] for variant in variants}
    seen = set()
    for index, record in enumerate(records):
        identity = record['chain'] + ':' + record['txn_hash'].lower()
        if identity in seen or type(record.get('label')) is not bool:
            raise ValueError('duplicate identity or missing adjudicated binary label')
        seen.add(identity)
        order = variants[index % len(variants):] + variants[:index % len(variants)]
        for variant in order:
            started = time.perf_counter()
            supplied = guidance.get(variant)
            if callable(supplied):
                supplied = supplied({key: value for key,value in record.items()
                                     if key not in {'label','ground_truth','annotation','vuln_type'}})
            observation = analyze(dict(record), variant, supplied)
            if type(observation.get('predicted_exploit')) is not bool:
                raise ValueError('analysis must return an executed boolean decision')
            output[variant].append(dict(observation, identity=identity, label=record['label'],
                duration_seconds=observation.get('duration_seconds', time.perf_counter()-started)))
            if 'expected_functions' in record:
                output[variant][-1]['expected_functions'] = record['expected_functions']
    return output


def _cost(row):
    if 'query_records' not in row:
        raise ValueError('missing cost usage records')
    total = 0.
    for call in row['query_records']:
        if 'cost_usd' not in call:
            raise ValueError('missing cost for query attempt')
        total += _finite(call['cost_usd'], 'cost')
        if call.get('usage_source') in {'estimated', 'estimate', 'reservation'} and call['cost_usd'] > 0:
            raise ValueError('estimated usage cannot prove measured API savings')
    return total


def _top(row):
    functions = row['ranked_functions']
    if not functions:
        return None
    first = functions[0]
    return (first['address'].lower(), first['function'])


def localization_metrics(rows):
    rows = list(rows)
    if not rows:
        raise ValueError('Localization requires nonempty executed rows')
    tp = fp = fn = correct = 0
    for row in rows:
        if 'expected_functions' not in row:
            raise ValueError('BLOCKED-BY-DATA: independently adjudicated function identities required')
        expected = {(item['address'].lower(),item['function']) for item in row['expected_functions']}
        predicted = {(item['address'].lower(),item['function']) for item in row['ranked_functions']}
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        correct += _top(row) in expected if expected else not predicted
    return {'n':len(rows),'top1_correct':correct,'top1_accuracy':correct/len(rows),
            'tp':tp,'fp':fp,'fn':fn,'micro_precision':tp/(tp+fp) if tp+fp else None,
            'micro_recall':tp/(tp+fn) if tp+fn else None,
            'micro_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}


def compare_runs(baseline, candidate):
    baseline, candidate = list(baseline), list(candidate)
    a = {r['identity']: r for r in baseline}
    b = {r['identity']: r for r in candidate}
    if not a or a.keys() != b.keys() or len(a) != len(baseline) or len(b) != len(candidate):
        raise ValueError('paired runs require equal unique transaction identities')
    keys = sorted(a)
    if any(a[k]['label'] != b[k]['label'] for k in keys):
        raise ValueError('paired runs require identical labels')
    labels = [a[k]['label'] for k in keys]
    ma = confusion_metrics(labels, [a[k]['predicted_exploit'] for k in keys])
    mb = confusion_metrics(labels, [b[k]['predicted_exploit'] for k in keys])
    ca, cb = sum(_cost(r) for r in baseline), sum(_cost(r) for r in candidate)
    ta = sum(_finite(r['duration_seconds'], 'duration') for r in baseline)
    tb = sum(_finite(r['duration_seconds'], 'duration') for r in candidate)
    eligible = [k for k in keys if _top(a[k]) is not None or _top(b[k]) is not None]
    localization = None
    if any('expected_functions' in row for row in baseline+candidate):
        la,lb = localization_metrics(baseline),localization_metrics(candidate)
        localization = {'baseline':la,'candidate':lb,
                        'top1_difference_pp':100*(lb['top1_accuracy']-la['top1_accuracy'])}
    return {'n': len(keys), 'baseline_metrics': ma, 'candidate_metrics': mb,
            'localization':localization,
            'accuracy_difference_pp': 100*(mb['accuracy']-ma['accuracy']),
            'f1_difference_pp': None if ma['f1'] is None or mb['f1'] is None else 100*(mb['f1']-ma['f1']),
            'baseline_cost_usd': ca, 'candidate_cost_usd': cb,
            'cost_savings_fraction': (ca-cb)/ca if ca else None,
            'latency_savings_fraction': (ta-tb)/ta if ta else None,
            'top1_eligible_n': len(eligible),
            'top1_agreement_fraction': sum(_top(a[k]) == _top(b[k]) for k in eligible)/len(eligible) if eligible else None}


def summarize_categories(rows):
    groups = defaultdict(list)
    fields = ('gas_used', 'function_calls', 'addresses', 'max_depth')
    for row in rows:
        for name in fields:
            if name not in row:
                raise ValueError('missing observed ' + name)
            _finite(row[name], name)
        if not row.get('category'):
            raise ValueError('missing adjudicated category')
        groups[row['category']].append(row)
    return {category: dict(n=len(items), **{name: sum(r[name] for r in items)/len(items) for name in fields})
            for category, items in groups.items()}


def summarize_confidence_categories(rows):
    """Table VI means from observed per-function Eq.4 component records.

    This function-weighted aggregation is explicit; it cannot supply missing
    observations or establish that a caller's categories are adjudicated.
    """
    from collections import defaultdict
    from faultseeker.core.confidence_scorer import DEFAULT_WEIGHTS
    groups,seen = defaultdict(list),set()
    names = {'pattern_match':'PMS','code_evidence':'CES',
             'txn_consistency':'TCS','llm_confidence':'LCS'}
    for row in rows:
        if not all(isinstance(row.get(k),str) and row[k] for k in
                   ['identity','function_identity','category']):
            raise ValueError('Observed transaction, function and category identities required')
        key = (row['identity'],row['function_identity'])
        if key in seen:
            raise ValueError('Duplicate confidence function observation')
        seen.add(key)
        confidence = row.get('confidence') or {}
        components = confidence.get('components') or {}
        if any(k not in components for k in names):
            raise ValueError('All observed confidence components are required')
        values = {name:_finite(components[name],'confidence component') for name in names}
        overall = _finite(confidence.get('overall'),'overall confidence')
        if any(not 0<=v<=1 for v in [*values.values(),overall]):
            raise ValueError('Confidence components must lie in [0,1]')
        computed = sum(DEFAULT_WEIGHTS[name]*value for name,value in values.items())
        if abs(computed-overall)>0.0002:
            raise ValueError('Observed confidence is inconsistent with Eq.4')
        groups[row['category']].append((row['identity'],values,overall))
    if not groups:
        raise ValueError('No observed confidence components available')
    return {category:{**{label:sum(values[name] for _,values,_ in items)/len(items)
                         for name,label in names.items()},
            'C_f':sum(overall for _,_,overall in items)/len(items),
            'n_functions':len(items),'n_transactions':len({identity for identity,_,_ in items}),
            'aggregation':'equal weight per observed function; no imputation'}
            for category,items in groups.items()}


def cohort_statistics(records):
    from collections import Counter
    records = list(records)
    if not records:
        raise ValueError('Nonempty authentic cohort required')
    fields = ('chain','vuln_type','vulnerability_class','reentrancy_label')
    if any(any(name not in row for name in fields) for row in records):
        raise ValueError('Missing adjudicated cohort taxonomy or reentrancy label')
    if any(type(row['reentrancy_label']) is not bool for row in records):
        raise ValueError('Reentrancy labels must be adjudicated booleans')
    counts = {field:dict(Counter(row[field] for row in records)) for field in fields[:3]}
    return {'n':len(records), 'counts':counts,
            'percentages':{field:{name:100*count/len(records) for name,count in rows.items()} for field,rows in counts.items()},
            'unique_chains':len(counts['chain']), 'unique_vulnerability_types':len(counts['vuln_type']),
            'reentrant_incidents':sum(row['reentrancy_label'] for row in records)}


def feasible_confusion_counts(n, positives, precision, recall, decimals=2):
    """Enumerate integer matrices compatible with rounded published targets."""
    if not (0 <= positives <= n) or type(n) is not int or type(positives) is not int:
        raise ValueError('Valid integer cohort sizes required')
    result = []
    for tp in range(positives+1):
        if not positives or round(tp/positives,decimals) != recall:
            continue
        for fp in range(n-positives+1):
            if tp+fp and round(tp/(tp+fp),decimals) == precision:
                result.append({'tp':tp,'fp':fp,'fn':positives-tp,'tn':n-positives-fp})
    return result


class PipelineObservationAdapter:
    """Use the same public production entry point for every experiment variant.

    A factory selects real detector/routing configurations; the adapter never
    derives predictions from the ground-truth label passed to the evaluator.
    """
    def __init__(self, pipeline_factory):
        self.pipeline_factory = pipeline_factory

    def __call__(self, record, variant, guidance):
        pipeline = self.pipeline_factory(variant)
        started = time.perf_counter()
        result = pipeline.analyze_transaction(txn_hash=record['txn_hash'], chain=record['chain'],
            analyst_guidance=guidance, analysis_context=record.get('analysis_context'))
        if result.get('error'):
            raise RuntimeError(result['error'])
        if result.get('analysis_complete') is False:
            raise RuntimeError('Production analysis is incomplete; no measurement is reported')
        verdict = result.get('rule_verdict')
        if isinstance(verdict, dict):
            verdict = verdict.get('verdict')
        return {'predicted_exploit': bool(result.get('potentially_vulnerable_functions')) or verdict == 'EXPLOIT',
                'triage_verdict':verdict,
                'decision_semantics':'reported_finding_or_deterministic_exploit; absence does not assert BENIGN',
                'ranked_functions': result.get('scored_functions', []),
                'query_records': result.get('query_records', []),
                'duration_seconds': time.perf_counter()-started,
                'stage2_bypassed': result.get('stage2_bypassed', False),
                'pipeline_result': result}
