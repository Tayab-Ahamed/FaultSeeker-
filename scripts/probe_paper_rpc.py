"""Explicit, counted read-only method probes for the configured dRPC endpoint."""
import argparse
import gzip
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if os.name == 'nt':
    sys.modules.setdefault('readline', None)

from dotenv import dotenv_values
from scripts.replay_historical_opcodes import MeteredRPC, account_prior_requests, REENTRANT, write_json


def observe(meter, method, params, mode):
    start = time.monotonic()
    row = {'method': method, 'mode': mode}
    try:
        data = meter.forward({'jsonrpc':'2.0','id':1,'method':method,'params':params})
        if data.get('error'):
            row.update(status='RPC-REJECTED', rpc_code=data['error'].get('code'))
        elif data.get('result') is None:
            row['status'] = 'NO-RESULT'
        else:
            result = data['result']
            row.update(status='RETURNED', result_type=type(result).__name__)
            if method == 'eth_chainId':
                row['chain_id'] = int(result, 16)
            if isinstance(result, dict):
                row['result_fields'] = sorted(result.keys())
            if isinstance(result, list):
                row['result_length'] = len(result)
    except Exception as error:
        row.update(status='REQUEST-FAILED', error_type=type(error).__name__)
    row['elapsed_ms'] = round((time.monotonic()-start)*1000)
    return row


def run(output):
    values = dotenv_values(ROOT/'.env')
    key = os.getenv('DRPC_API_KEY') or values.get('DRPC_API_KEY') or ''
    raw = os.getenv('DRPC_RPC_URL') or values.get('DRPC_RPC_URL') or ''
    endpoint = raw.replace('{chain}', 'eth').replace('{api_key}', quote(key, safe=''))
    hostname = urlsplit(endpoint).hostname or ''
    if urlsplit(endpoint).scheme != 'https' or not (hostname=='drpc.org' or hostname.endswith('.drpc.org')
            or hostname=='drpc.live' or hostname.endswith('.drpc.live')):
        raise ValueError('HTTPS dRPC endpoint required')
    with gzip.open(ROOT/'reports/historical_replay'/(REENTRANT+'.json.gz'), 'rt', encoding='utf-8') as handle:
        capture = json.load(handle)
    tx = capture['transaction']
    block = hex(capture['fork_parent_block'])
    meter = MeteredRPC(endpoint, ROOT/'data/research/spend_ledger.json', max_requests=40)
    account_prior_requests(meter.guard, 7)
    specs = [
        ('eth_chainId', [], 'network identity'),
        ('eth_blockNumber', [], 'head'),
        ('eth_getTransactionByHash', [REENTRANT], 'historical identity'),
        ('eth_getTransactionReceipt', [REENTRANT], 'historical receipt'),
        ('eth_getBlockByHash', [tx['blockHash'], False], 'historical block'),
        ('eth_getBlockByNumber', [block, False], 'parent block'),
        ('eth_getBalance', [tx['to'], block], 'archive balance'),
        ('eth_getTransactionCount', [tx['from'], block], 'archive nonce'),
        ('eth_getCode', [tx['to'], block], 'archive bytecode'),
        ('eth_getStorageAt', [tx['to'], '0x0', block], 'archive slot'),
        ('eth_call', [{'to':tx['from'],'data':'0x'}, block], 'EOA no-op call'),
        ('eth_getLogs', [{'blockHash':tx['blockHash'], 'address':tx['to']}], 'historical logs'),
        ('debug_traceTransaction', [REENTRANT, {'tracer':'callTracer','timeout':'10s'}], 'callTracer'),
        ('debug_traceTransaction', [REENTRANT, {'disableMemory':True,'disableStack':False,'disableStorage':False}], 'opcode logger'),
        ('trace_replayTransaction', [REENTRANT, ['trace','stateDiff']], 'Parity trace/stateDiff fallback'),
    ]
    results = []
    for method, params, mode in specs:
        result = observe(meter, method, params, mode)
        results.append(result)
        print(json.dumps(result), flush=True)
    try:
        batch = meter.forward([{'jsonrpc':'2.0','id':11,'method':'eth_chainId','params':[]},
                               {'jsonrpc':'2.0','id':12,'method':'eth_blockNumber','params':[]}])
        valid = (isinstance(batch, list) and {r.get('id') for r in batch} == {11,12}
                 and all(r.get('result') is not None and not r.get('error') for r in batch))
        results.append({'method':'JSON-RPC batch','mode':'two reads; correlation by id',
                        'status':'RETURNED' if valid else 'INVALID-OR-REJECTED'})
    except Exception as error:
        results.append({'method':'JSON-RPC batch','status':'REQUEST-FAILED','error_type':type(error).__name__})
    report = {'scope':'observed configured endpoint only; RETURNED is not a full correctness proof',
        'endpoint_uses_chain_template':'{chain}' in raw,
        'observations':results, 'rpc_usage':meter.summary(),
        'untested_scope':'Other paper chains and sustained-load fault recovery not established by these probes.'}
    write_json(Path(output), report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--output',type=Path, default=ROOT/'reports/claim_closure/rpc_capabilities.json')
    args = parser.parse_args()
    if not args.execute_live:
        raise SystemExit('No calls dispatched; pass --execute-live.')
    run(args.output)
