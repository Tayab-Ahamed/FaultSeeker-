"""Numeric distribution features from whitelisted predictions, no target inputs."""
import math
import numpy as np
from faultseeker.function_analysis.function_ranker import rerank_saved_predictions
NAMES=('log_count','log_function_rows','log_function_diversity','log_paths','log_parents','max_depth','mean_depth','std_depth','best_rank_reciprocal','sum_rank_reciprocal','top_count_fraction','count_per_parent','depth_range','repeated_path_fraction')
def features(predictions,address):
    allowed=('code_address','address','function','function_name','count','supporting_call_depths')
    clean=[{k:p[k] for k in allowed if k in p} for p in predictions]
    ranked=rerank_saved_predictions(clean)
    selected=[(i,p) for i,p in enumerate(ranked,1) if str(p.get('code_address') or p.get('address') or '').lower()==address]
    if not selected:return [0.]*len(NAMES)
    counts=[max(0,int(p.get('count') or 0)) for i,p in selected]
    paths=[tuple(path) for i,p in selected for path in p.get('supporting_call_depths') or [] if isinstance(path,(tuple,list))]
    depths=[len(p) for p in paths] or [0]
    parents={p[:-1] for p in paths if p}
    total=sum(counts)
    return [math.log1p(total),math.log1p(len(selected)),math.log1p(len({str(p.get('function') or p.get('function_name') or '') for i,p in selected})),math.log1p(len(paths)),math.log1p(len(parents)),max(depths),float(np.mean(depths)),float(np.std(depths)),1/selected[0][0],sum(1/i for i,p in selected),max(counts)/max(1,total),math.log1p(total/max(1,len(parents))),max(depths)-min(depths),1-len(set(paths))/max(1,len(paths)) if paths else 0.]
