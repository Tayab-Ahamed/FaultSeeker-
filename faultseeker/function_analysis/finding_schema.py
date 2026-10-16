"""Pure closed-set validation of model findings and final finding order.

Observed execution identities are authoritative. No ABI alias, source lookup,
address heuristic, or model-supplied depth can manufacture an observed finding.
Validation returns fresh objects and never mutates caller state.
"""
import math


def _observed_identities(observed_memo):
    if not isinstance(observed_memo,dict):
        raise ValueError('Observed function call memo must be a dictionary')
    result={}
    for identity,calls in observed_memo.items():
        if not calls:continue
        if not isinstance(identity,str) or not isinstance(calls,(list,tuple)):
            raise ValueError('Observed identity and call list required')
        function,separator,address=identity.rpartition('::')
        if (not separator or not function or not address or function.strip()!=function
                or address.strip()!=address or '::' in function):
            raise ValueError('Malformed observed function identity')
        key=function+'_'+address.lower()
        if key in result:raise ValueError('Duplicate canonical observed identity')
        depths=[]
        for call in calls:
            if not isinstance(call,dict):raise ValueError('Observed call record required')
            depth=call.get('depth')
            if (not isinstance(depth,(list,tuple))
                    or any(type(index) is not int or index<0 for index in depth)):
                raise ValueError('Observed call path required for finding depth')
            depths.append(len(depth))
        result[key]=max(depths)
    return result


def normalize_findings(response,observed_memo):
    """Validate every finding against exact observed function/address pairs.

    Preserve the observed function spelling; addresses compare case-insensitively
    and canonical output uses lowercase addresses. Confidence is a finite numeric
    score in [0,1], including zero. Depth derives only from observed calls.
    """
    if not isinstance(response,dict):raise ValueError('Finding response must be a dictionary')
    observed=_observed_identities(observed_memo)
    normalized={}
    for identity,record in response.items():
        if not isinstance(identity,str):raise ValueError('Finding identity must be a string')
        function,separator,address=identity.rpartition('_')
        if not separator or not function or not address:
            raise ValueError('Finding identity must include function and address')
        key=function+'_'+address.lower()
        if key not in observed:raise ValueError('Finding identity is not observed in the transaction')
        if key in normalized:raise ValueError('Duplicate canonical finding identity')
        if isinstance(record,dict):
            if 'evidence' not in record or 'confidence_score' not in record:
                raise ValueError('Finding evidence and confidence required')
            evidence,confidence=record['evidence'],record['confidence_score']
        elif isinstance(record,(list,tuple)) and len(record)==2:
            evidence,confidence=record
        else:raise ValueError('Finding must be an evidence/confidence record')
        if not isinstance(evidence,str) or not evidence.strip():
            raise ValueError('Finding evidence must be a nonblank string')
        if (type(confidence) not in (int,float) or not 0<=confidence<=1
                or not math.isfinite(confidence)):
            raise ValueError('Finding confidence must be a finite confidence score')
        normalized[key]={'evidence':evidence,'confidence_score':float(confidence),'depth':observed[key]}
    return normalized


def validate_finding_order(order,offered):
    """Accept only a complete, unique, exact permutation of offered keys."""
    if not isinstance(offered,(dict,list,tuple,set,frozenset)):
        raise ValueError('Offered finding identities must be a collection')
    keys=list(offered)
    if (not isinstance(order,list) or any(not isinstance(k,str) for k in order)
            or any(not isinstance(k,str) for k in keys)
            or len(set(keys))!=len(keys) or len(order)!=len(keys)
            or len(set(order))!=len(order) or set(order)!=set(keys)):
        raise ValueError('Finding order must be an exact permutation of offered identities')
    return list(order)
