"""Address graph features from actual saved prediction call paths."""
from collections import defaultdict
from scripts.research.address_coverage_lane_a import ALLOWED
from scripts.research import address_ranking_phase1 as base
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions

FEATURES=('baseline_reciprocal','path_share','function_share','entry_share','leaf_share','subtree_share','recurrence','incoming_degree','outgoing_degree')

def extract_topology(predictions):
    clean=[{k:p[k] for k in ALLOWED if k in p} for p in predictions]
    evidence=base.extract_evidence(rerank_saved_predictions(clean),'')
    addresses={r['address'] for r in evidence}
    paths=defaultdict(set)
    functions=defaultdict(set)
    for p in clean:
        a=str(p.get('code_address') or p.get('address') or '').lower()
        if a not in addresses:
            continue
        functions[a].add(str(p.get('function') or p.get('function_name') or ''))
        for value in p.get('supporting_call_depths') or []:
            if isinstance(value,(list,tuple)) and all(isinstance(x,int) for x in value):
                paths[tuple(value)].add(a)
    own={a:{p for p,owners in paths.items() if a in owners} for a in addresses}
    incoming=defaultdict(set)
    outgoing=defaultdict(set)
    for p,owners in paths.items():
        if p and p[:-1] in paths:
            for parent in paths[p[:-1]]:
                for child in owners:
                    if parent!=child:
                        outgoing[parent].add(child)
                        incoming[child].add(parent)
    total=max(1,len(paths))
    total_functions=max(1,sum(len(x) for x in functions.values()))
    result=[]
    for e in evidence:
        a=e['address']; ap=own[a]
        entry=sum(not p or p[:-1] not in paths for p in ap)
        leaf=sum(not any(len(q)>len(p) and q[:len(p)]==p for q in paths) for p in ap)
        subtree={q for p in ap for q in paths if len(q)>=len(p) and q[:len(p)]==p}
        recurrent=sum(any(a in paths.get(p[:j],set()) for j in range(len(p))) for p in ap)
        result.append(dict(address=a,baseline_reciprocal=e['best_reciprocal'],path_share=len(ap)/total,
            function_share=len(functions[a])/total_functions,entry_share=entry/total,leaf_share=leaf/total,
            subtree_share=len(subtree)/total,recurrence=recurrent/max(1,len(ap)),
            incoming_degree=len(incoming[a])/max(1,len(addresses)-1),outgoing_degree=len(outgoing[a])/max(1,len(addresses)-1)))
    return result
