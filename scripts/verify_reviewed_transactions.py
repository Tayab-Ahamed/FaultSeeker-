"""Retry only source-reviewed identities; preserve every RPC attempt and meter it."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.modules.setdefault('readline',None)
from dotenv import dotenv_values
from benchmark.evidence_manifest import CHAIN_IDS
from benchmark.research_protocol import bind, write_json
from scripts.rebuild_authentic_cohort import BASE, drpc_url, identity_observation
from scripts.replay_historical_opcodes import MeteredRPC

PUBLIC={'arbitrum':('https://arb1.arbitrum.io/rpc','https://docs.arbitrum.io/chain-info'),
        'gnosis':('https://rpc.gnosischain.com/','https://docs.gnosischain.com/tools/RPC%20Providers/')}


def run():
    endpoint=dotenv_values(ROOT/'.env').get('DRPC_RPC_URL')
    if not endpoint:
        raise ValueError('DRPC_RPC_URL required')
    accounting=[]
    for row in json.loads((BASE/'candidate_pool.json').read_text()):
        if not row.get('incident_id','').startswith('reviewed:'):
            continue
        target=BASE/'rpc'/row['chain']/(row['txn_hash']+'.json')
        if target.exists() and json.loads(target.read_text()).get('identity_receipt_match'):
            continue
        routes=[('authorized-dRPC',drpc_url(endpoint,row['chain']),None)]
        if row['chain'] in PUBLIC:
            url,doc=PUBLIC[row['chain']]
            routes.append(('official-public-'+row['chain'],url,doc))
        for label,url,doc in routes:
            meter=MeteredRPC(url,ROOT/'data/research/spend_ledger.json',max_requests=3)
            attempt={'chain':row['chain'],'txn_hash':row['txn_hash'],'provider':label,
                     'provider_documentation':doc,'observed_at':datetime.now(timezone.utc).isoformat()}
            try:
                chain=int(meter.rpc('eth_chainId',[]),16)
                if chain!=CHAIN_IDS[row['chain']]:
                    raise ValueError('Wrong chain ID')
                responses=meter.forward([{'jsonrpc':'2.0','id':1,'method':'eth_getTransactionByHash','params':[row['txn_hash']]},
                    {'jsonrpc':'2.0','id':2,'method':'eth_getTransactionReceipt','params':[row['txn_hash']]}])
                observed=identity_observation(row,chain,responses)
                observed['provider']=label
                attempt['observation']=observed
            except Exception as error:
                attempt['error_type']=type(error).__name__
                # Transport exceptions can include credentials: retain only type.
            attempt['accounting']=meter.summary()
            attempt_file=BASE/'rpc_attempts'/row['chain']/row['txn_hash']/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
            write_json(attempt_file,attempt)
            accounting.append(bind(attempt_file,ROOT))
            write_json(BASE/'rpc_retry_accounting.json',accounting)
            valid=attempt.get('observation',{}).get('identity_receipt_match',False)
            print(row['incident_id'],row['chain'],label,'identity verified',valid,flush=True)
            if valid:
                if target.exists():
                    old=BASE/'rpc_attempts'/row['chain']/row['txn_hash']/'previous-selected.json'
                    if not old.exists():
                        old.write_bytes(target.read_bytes())
                write_json(target,observed)
                break


if __name__=='__main__':
    run()
