"""Attempt canonical-prefix Anvil replay for each admitted Ethereum transaction.

Acquisition only: no detector is scored and no held-out partition is loaded.
Receipt, block environment, prefix order and storage ownership must all pass the
existing historical replay validator. Failures remain explicit evidence gaps.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from dotenv import dotenv_values
from benchmark.research_protocol import admit, bind, write_json, acquisition_records
from scripts.rebuild_authentic_cohort import BASE
from scripts.replay_historical_opcodes import MeteredRPC, replay_one, upstream_proxy, validate_recorded_capture


def run(transaction_hashes=None, mine_timeout=300, use_prestate_cache=False):
    if type(mine_timeout) is not int or not 1 <= mine_timeout <= 900:
        raise ValueError('Mining timeout must be bounded to 1..900 seconds')
    values=dotenv_values(ROOT/'.env')
    endpoint=values.get('DRPC_RPC_URL')
    if not endpoint:
        raise ValueError('DRPC_RPC_URL required')
    output=BASE/'opcodes'
    rows=[r for r in acquisition_records(ROOT,BASE/'admitted_records.json') if r['chain']=='eth']
    authorized_ids={r['chain']+':'+r['txn_hash'] for r in rows}
    if transaction_hashes:
        if not set(transaction_hashes)<={r['txn_hash'] for r in rows}:
            raise ValueError('Requested transaction is outside the authorized Ethereum acquisition partition')
        rows=[r for r in rows if r['txn_hash'] in transaction_hashes]
    from scripts.capture_authentic_prestate import archive
    index=BASE/('opcode_acquisition_train.json' if (ROOT/'benchmark/eval_split.json').exists() else 'opcode_acquisition.json')
    previous=json.loads(index.read_text()).get('attempts',[]) if index.exists() else []
    if any(r.get('identity') not in authorized_ids for r in previous):
        raise ValueError('Opcode acquisition history contains non-train identities')
    archive(index,BASE/'opcode_history')
    meter=MeteredRPC(endpoint,ROOT/'data/research/spend_ledger.json',max_requests=12000)
    records=[]
    for row in rows:
        if not admit(row,ROOT)['accepted']:
            raise ValueError('Invalidated admission')
        target=output/(row['txn_hash']+'.json.gz')
        record={'identity':'eth:'+row['txn_hash'],'status':'UNAVAILABLE'}
        before=meter.count
        active_meter=meter
        try:
            if target.exists():
                validate_recorded_capture(target,row['txn_hash'])
                record['status']='VALIDATED_RECORDED_CAPTURE'
            else:
                if use_prestate_cache:
                    from scripts.pinned_prestate_rpc import PinnedPrestateRPC
                    active_meter=PinnedPrestateRPC(meter,row,ROOT)
                with upstream_proxy(active_meter) as proxy:
                    record['capture']=replay_one(row['txn_hash'],'provenance-admitted exploit; label not used during replay',
                        active_meter,proxy,str(ROOT/'build/tools/anvil.exe'),output,mine_timeout=mine_timeout)
                record['status']='CAPTURED_CANONICAL_OPCODES'
            record['artifact']=bind(target,ROOT)
        except Exception as error:
            message=str(error)
            for key,value in values.items():
                if value and len(value)>10 and ('KEY' in key or 'URL' in key):
                    message=message.replace(value,'[REDACTED]')
            record.update(error_type=type(error).__name__,reason=message[:600])
            if getattr(error,'failure_evidence',None):
                record['failure_evidence']=error.failure_evidence
        record['outbound_rpc_requests']=meter.count-before
        if hasattr(active_meter,'cache_evidence'):
            record['prestate_read_cache']=active_meter.cache_evidence()
        records.append(record)
        selected={r['identity'] for r in records}
        merged=records+[r for r in previous if r['identity'] not in selected]
        write_json(index,{'attempts':merged,'accounting':meter.summary(),
            'accounting_scope':'Current invocation only; prior observations are preserved per identity and archived per run'})
        print(row['txn_hash'][:12],record['status'],record['outbound_rpc_requests'],flush=True)
        if meter.count>=meter.max_requests:
            break



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transaction',action='append')
    parser.add_argument('--mine-timeout',type=int,default=300)
    parser.add_argument('--prestate-cache',action='store_true',help='Exact-parent observed prestate cache; first-in-block pre-Shanghai Ethereum only')
    args=parser.parse_args()
    run(args.transaction,args.mine_timeout,args.prestate_cache)
