"""Selected research address localizer; real learned inference without label inputs."""
from pathlib import Path
import sys
_RESEARCH=Path(__file__).resolve().parent
if str(_RESEARCH) not in sys.path:sys.path.insert(0,str(_RESEARCH))
import address_margin_lane_c as margin
from scripts.research import address_coverage_lane_a as coverage
from scripts.research import address_topology_lane_a as topology
from scripts.research import names_semantics_corrected as lexical

CONFIG=('basic','svc',10.)


def prepare(predictions,trace_text):
    row=margin.prepare(predictions,trace_text,coverage,topology,lexical)
    row['observed_addresses']=[e['address'] for e in coverage.extract_candidates(predictions,trace_text)]
    return row


def fit(rows,train_indices):
    return margin.fit(rows,train_indices,CONFIG)


def append_observed(prefix,row):
    seen=set(prefix)
    result=list(prefix)
    for address in row['observed_addresses']:
        if address not in seen:
            result.append(address);seen.add(address)
    return result


def predict(bundle,row):
    return append_observed(margin.predict(bundle,row),row)
