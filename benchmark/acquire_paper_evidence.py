"""Explicit live acquisition boundary; importing this module makes no requests."""
import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from benchmark.evidence_manifest import CHAIN_IDS, HASH, digest_file


def _rpc(url, method, params):
    request = Request(url, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),
                      headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get('error') or payload.get('result') is None:
        raise RuntimeError('RPC acquisition failed: ' + method)
    return payload['result']


def _replay(txn_hash, url):
    binary = os.getenv('CAST_BINARY') or shutil.which('cast')
    if not binary:
        raise RuntimeError('PENDING-CREDENTIALS: CAST_BINARY required for replay verification')
    result = subprocess.run([binary,'run','--quick',txn_hash,'--rpc-url',url],
                            capture_output=True, timeout=300)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError('Foundry replay failed; acquisition remains unverified')
    return {'tool':'cast run --quick', 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest()}


def capture_transaction(txn_hash, chain, endpoints, output, rpc=None, replay=None):
    if chain not in CHAIN_IDS or not HASH.fullmatch(txn_hash):
        raise ValueError('valid transaction hash and supported chain required')
    if len(endpoints) != 2 or len({urlparse(url).hostname for url in endpoints}) != 2:
        raise ValueError('two independent RPC provider hosts required')
    rpc, replay = rpc or _rpc, replay or _replay
    snapshots = []
    for url in endpoints:
        if int(rpc(url,'eth_chainId',[]),16) != CHAIN_IDS[chain]:
            raise ValueError('RPC chain mismatch')
        tx = rpc(url,'eth_getTransactionByHash',[txn_hash])
        receipt = rpc(url,'eth_getTransactionReceipt',[txn_hash])
        block = rpc(url,'eth_getBlockByNumber',[receipt['blockNumber'],False])
        if (tx.get('hash','').lower() != txn_hash.lower() or
                receipt.get('transactionHash','').lower() != txn_hash.lower() or
                tx.get('blockHash') != receipt.get('blockHash') or
                block.get('hash') != receipt.get('blockHash')):
            raise ValueError('canonical transaction identity mismatch')
        snapshots.append((tx,receipt,block))
    if any(snapshots[0][i] != snapshots[1][i] for i in (0,1)):
        raise ValueError('independent provider transaction/receipt mismatch')
    call = rpc(endpoints[0], 'debug_traceTransaction', [txn_hash, {'tracer':'callTracer','timeout':'60s'}])
    opcode = rpc(endpoints[0], 'debug_traceTransaction', [txn_hash, {'disableStack':False,'disableMemory':True,'disableStorage':False}])
    if not isinstance(call,dict) or not isinstance(opcode,dict) or not opcode.get('structLogs') or opcode.get('error'):
        raise ValueError('complete call and opcode traces required')
    replay_proof = replay(txn_hash,endpoints[0])
    if not replay_proof:
        raise ValueError('independent replay proof required')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tx,receipt,_ = snapshots[0]
    paths = {}
    payloads = {'transaction':tx, 'receipt':receipt, 'trace':{
        'transaction_hash':txn_hash,'chain':chain,'raw_trace':{'call':call,'opcode':opcode},
        'complete':True,'capture_version':'faultseeker-evidence-v1',
        'tracer_config':{'call':'callTracer','opcode':'structLogs, stack/storage enabled'}}}
    for name,payload in payloads.items():
        path = output/(name+'.json')
        path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        paths[name] = path.name
    proof = {'mode':'live-rpc-and-replay','chain_id':CHAIN_IDS[chain],
             'rpc_endpoints':[urlparse(url).hostname for url in endpoints],
             'canonical_block_hash':receipt['blockHash'],
             'verified_at':datetime.now(timezone.utc).isoformat(),
             'tool_versions':{'python':platform.python_version(),'replay':replay_proof}}
    proof.update({name+'_sha256':digest_file(output/path) for name,path in paths.items()})
    (output/'verification.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    return dict(paths,verification='verification.json',txn_hash=txn_hash,chain=chain,
                missing=['independent source artifacts','independent annotations','ground truth'])
