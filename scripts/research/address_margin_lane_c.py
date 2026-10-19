"""Reusable label-free preparation and train-index-only lexical ranker fitting."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from scipy.optimize import minimize
from scipy.special import logsumexp
import address_learned_lane_c as learner
import address_behavior_lane_c as behavior

def prepare(predictions,trace,coverage,topology,lexical):
    allowed=('code_address','address','function','function_name','count','supporting_call_depths')
    predictions=[{k:p[k] for k in allowed if k in p} for p in predictions]
    previous={e['address']:(j,e) for j,e in enumerate(learner.base.extract_evidence(learner.base.rerank_saved_predictions(predictions),trace))}
    evidence=coverage.extract_candidates(predictions,trace)
    topo={e['address']:e for e in topology.extract_topology(predictions)}
    basic=[];rich=[]
    for e in evidence:
        old=previous.get(e['address'])
        values=[float(old[1][k]) if old else 0. for k in learner.FEATURES]+[1/(old[0]+1) if old else 0.]
        basic.append(values)
        rich.append(values+[float(e[k]) for k in coverage.FEATURES]+behavior.features(predictions,e['address'])+[float(topo.get(e['address'],{}).get(k,0.)) for k in topology.FEATURES])
    keep=[i for i,v in enumerate(basic) if v[0]>0]
    evidence=[evidence[i] for i in keep];basic=[basic[i] for i in keep];rich=[rich[i] for i in keep]
    return {'evidence':evidence,'basic':basic,'rich':rich,'docs':lexical.documents([e['address'] for e in evidence],predictions,trace)}

def transform(bundle,row):
    lexical=bundle['vectorizer'].transform(row['docs']).toarray()*3
    numeric=bundle['scaler'].transform(row[bundle['mode']])
    return np.column_stack((numeric,lexical))

def fit(rows,train,config):
    mode,kind,param=config
    docs=[d for i in train for d in rows[i]['docs']]
    numeric=np.asarray([v for i in train for v in rows[i][mode]])
    bundle={'mode':mode,'vectorizer':TfidfVectorizer(token_pattern=r'(?u)\b[a-z]{2,}\b',ngram_range=(1,2)).fit(docs),'scaler':StandardScaler().fit(numeric)}
    batches=[]
    for i in train:
        row=rows[i]; x=transform(bundle,row)
        y=np.array([e['address'] in row['targets'] for e in row['evidence']])
        batches.append((x,y,row['group_weight']))
    if kind=='pairwise':
        pair_x=[];pair_y=[];pair_w=[]
        for x,y,w in batches:
            pairs=[(p,n) for p in range(len(y)) if y[p] for n in range(len(y)) if not y[n]]
            for p,n in pairs:
                pair_x.extend([x[p]-x[n],x[n]-x[p]]);pair_y.extend([1,0]);pair_w.extend([w/(2*len(pairs))]*2)
        model=LogisticRegression(C=param,max_iter=2000,random_state=learner.base.SEED,fit_intercept=False)
        model.fit(np.asarray(pair_x),pair_y,sample_weight=pair_w)
        bundle['coef']=model.coef_[0];bundle['intercept']=0.
    elif kind in ('logistic','svc'):
        model=(LinearSVC(C=param,max_iter=20000,dual='auto',random_state=learner.base.SEED) if kind=='svc' else LogisticRegression(C=param,max_iter=10000,random_state=learner.base.SEED))
        model.fit(np.concatenate([x for x,y,w in batches]),np.concatenate([y for x,y,w in batches]),sample_weight=np.concatenate([np.full(len(x),w/len(x)) for x,y,w in batches]))
        bundle['coef']=model.coef_[0];bundle['intercept']=float(model.intercept_[0])
    else:
        eligible=[(x,y,w) for x,y,w in batches if y.any()]
        total=sum(w for x,y,w in eligible)
        def objective(coef):
            loss=param*np.dot(coef,coef)/2;grad=param*coef.copy()
            for x,y,w in eligible:
                scores=x@coef;normal=logsumexp(scores);positive=logsumexp(scores[y])
                loss+=w*(normal-positive)/total
                grad+=w*(np.exp(scores-normal)@x-np.exp(scores[y]-positive)@x[y])/total
            return loss,grad
        result=minimize(objective,np.zeros(batches[0][0].shape[1]),jac=True,method='L-BFGS-B',options={'maxiter':1000,'ftol':1e-12})
        if not result.success: raise RuntimeError(result.message)
        bundle['coef']=result.x;bundle['intercept']=0.
    return bundle

def predict(bundle,row):
    if not row['evidence']:return []
    scores=transform(bundle,row)@bundle['coef']+bundle['intercept']
    return [row['evidence'][i]['address'] for i in sorted(range(len(scores)),key=lambda i:(-scores[i],i))]




