"""Opt-in, bounded acquisition of preregistered historical plain EOA controls.

Preserves parsed JSON RPC envelopes, not original HTTP octets. No detector or
model participates in selection; no execution trace or missing state is invented.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmark.research_protocol import bind, transaction_chain_id, write_json
from scripts.replay_historical_opcodes import MeteredRPC

STUDY = 'distinct-plain-eoa-controls-v1'
BLOCKS = list(range(14700000, 16575001, 125000))
ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}\Z')
HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')
MAX_REQUESTS = 512


def integer(value):
    if type(value) is not str or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError('Invalid RPC quantity')
    return int(value, 16)


def cheap_reasons(tx, hashes, senders, recipients):
    reasons = []
    if not isinstance(tx, dict):
        return ['MALFORMED_TRANSACTION']
    key, sender, recipient = (str(tx.get(k, '')).lower() for k in ('hash', 'from', 'to'))
    if not HASH.fullmatch(key): reasons.append('INVALID_TRANSACTION_HASH')
    if not ADDRESS.fullmatch(sender): reasons.append('INVALID_SENDER')
    if not ADDRESS.fullmatch(recipient): reasons.append('INVALID_DESTINATION')
    elif int(recipient, 16) <= 65535: reasons.append('PRECOMPILE_OR_RESERVED_DESTINATION')
    if key in hashes: reasons.append('DUPLICATE_HASH')
    if sender in senders: reasons.append('REUSED_SENDER')
    if recipient in recipients: reasons.append('REUSED_RECIPIENT')
    if sender == recipient: reasons.append('SENDER_EQUALS_RECIPIENT')
    try:
        if integer(tx.get('value')) <= 0: reasons.append('NONPOSITIVE_VALUE')
    except (ValueError, TypeError): reasons.append('INVALID_VALUE')
    if tx.get('input') != '0x': reasons.append('NONEMPTY_INPUT')
    try:
        if transaction_chain_id(tx) != 1: reasons.append('CHAIN_ID_MISMATCH')
    except (ValueError, TypeError, KeyError): reasons.append('UNVERIFIABLE_CHAIN_ID')
    return reasons


def eligibility(tx, block, receipt, codes, hashes, senders, recipients):
    reasons = cheap_reasons(tx, hashes, senders, recipients)
    if not isinstance(receipt, dict): return reasons + ['MISSING_RECEIPT']
    try:
        index = integer(tx['transactionIndex'])
        if (tx['blockHash'] != block['hash'] or tx['blockNumber'] != block['number']
            or block['transactions'][index]['hash'] != tx['hash']
            or any(receipt.get(k) != tx.get(t) for k,t in (
                ('transactionHash','hash'),('blockHash','blockHash'),
                ('blockNumber','blockNumber'),('transactionIndex','transactionIndex')))):
            reasons.append('CANONICAL_RECEIPT_MISMATCH')
    except (ValueError, TypeError, KeyError, IndexError): reasons.append('CANONICAL_RECEIPT_MISMATCH')
    if receipt.get('status') != '0x1': reasons.append('RECEIPT_NOT_SUCCESS')
    if receipt.get('logs') != []: reasons.append('NONEMPTY_LOGS')
    for i, label in enumerate(('DESTINATION_PARENT_CODE','DESTINATION_INCLUSION_CODE','SENDER_PARENT_CODE')):
        if len(codes) <= i or codes[i] != '0x': reasons.append(label + '_NOT_EMPTY_OR_UNOBSERVED')
    return list(dict.fromkeys(reasons))


class RequestBoundReached(RuntimeError):
    pass


def acquire(meter, preregistration, output, root=ROOT):
    output, root = Path(output), Path(root)
    output.mkdir(parents=True, exist_ok=True)
    request_count = 0
    def request(method, params):
        nonlocal request_count
        if request_count >= MAX_REQUESTS: raise RequestBoundReached('Control request bound reached')
        request_count += 1
        payload = {'jsonrpc':'2.0','id':request_count,'method':method,'params':params}
        try:
            response = meter.forward(payload)
            # JSON RPC errors can echo credentials. Preserve only safe error code.
            if isinstance(response, dict) and response.get('error'):
                response = {'jsonrpc':response.get('jsonrpc'),'id':response.get('id'),
                            'error':{'code':response['error'].get('code'),'message':'Upstream RPC error; text redacted'}}
            return {'request':payload,'response':response}
        except (OSError, RuntimeError, ValueError) as error:
            return {'request':payload,'transport_error_type':type(error).__name__}
    def result(record):
        response = record.get('response')
        return response.get('result') if isinstance(response, dict) and not response.get('error') else None
    chain = request('eth_chainId', [])
    accepted, inspected, blocks = [], [], []
    hashes, senders, recipients = set(), set(), set()
    write_json(output/'chain.json', chain)
    stop = None
    if result(chain) != '0x1': stop = 'CHAIN_ID_UNVERIFIED'
    try:
        for number in ([] if stop else preregistration['block_numbers']):
            if stop or len(accepted) >= preregistration['target_count']: break
            if request_count + 2 > MAX_REQUESTS:
                stop='REQUEST_BOUND_REACHED'; break
            block_record = request('eth_getBlockByNumber', [hex(number), True])
            block = result(block_record)
            block_path = output/'blocks'/f'{number}.json'
            write_json(block_path, block_record)
            if not isinstance(block,dict) or block.get('number') != hex(number) or not HASH.fullmatch(str(block.get('hash',''))) or not isinstance(block.get('transactions'),list):
                blocks.append({'number':number,'status':'BLOCK_UNAVAILABLE','record':bind(block_path,root)}); continue
            parent_record = request('eth_getBlockByHash', [block.get('parentHash'), False])
            parent_path = output/'blocks'/f'{number}-parent.json'
            write_json(parent_path,parent_record)
            parent = result(parent_record)
            block_binding = {'block':bind(block_path,root),'parent':bind(parent_path,root)}
            if not isinstance(parent,dict) or parent.get('hash') != block.get('parentHash') or parent.get('number') != hex(number-1):
                blocks.append({'number':number,'status':'PARENT_UNVERIFIED',**block_binding}); continue
            admitted = 0
            for index,tx in enumerate(block['transactions']):
                if admitted >= 4 or len(accepted) >= preregistration['target_count']: break
                record = {'chain':'eth','chain_id':1,'transaction':tx,'canonical':block_binding,'requests':[]}
                reasons = cheap_reasons(tx, hashes, senders, recipients)
                if not reasons and (tx.get('transactionIndex') != hex(index) or tx.get('blockHash') != block['hash'] or tx.get('blockNumber') != block['number']):
                    reasons = ['CANONICAL_TRANSACTION_MISMATCH']
                if not reasons and request_count + 4 > MAX_REQUESTS:
                    reasons=['REQUEST_BOUND_BEFORE_ELIGIBILITY']; stop='REQUEST_BOUND_REACHED'
                if not reasons:
                    receipt_record = request('eth_getTransactionReceipt',[tx['hash']])
                    record['requests'].append(receipt_record)
                    receipt = result(receipt_record); record['receipt'] = receipt
                    if not isinstance(receipt,dict) or receipt.get('status') != '0x1' or receipt.get('logs') != []:
                        reasons = eligibility(tx,block,receipt,[],hashes,senders,recipients)
                    else:
                        codes=[]
                        for address, blockhash in ((tx['to'],parent['hash']),(tx['to'],block['hash']),(tx['from'],parent['hash'])):
                            response=request('eth_getCode',[address,{'blockHash':blockhash,'requireCanonical':True}])
                            record['requests'].append(response);codes.append(result(response))
                        reasons=eligibility(tx,block,receipt,codes,hashes,senders,recipients)
                record['eligibility_reasons']=reasons
                record['accepted']=not reasons
                if not reasons:
                    # Selection is final before optional execution tracing.
                    hashes.add(tx['hash'].lower());senders.add(tx['from'].lower());recipients.add(tx['to'].lower())
                    admitted+=1
                    if request_count < MAX_REQUESTS:
                        trace=request('debug_traceTransaction',[tx['hash'],{'tracer':'callTracer'}])
                        record['requests'].append(trace)
                        value=result(trace)
                        valid_trace = (isinstance(value,dict) and not value.get('error')
                            and value.get('type') == 'CALL' and value.get('input') == tx['input']
                            and str(value.get('from','')).lower() == tx['from'].lower()
                            and str(value.get('to','')).lower() == tx['to'].lower()
                            and value.get('value') == tx['value'] and not value.get('calls'))
                        record['call_trace']={'available':valid_trace,'result':value,
                            'reason':None if valid_trace else 'UNAVAILABLE_OR_IDENTITY_MISMATCH'}
                    else: record['call_trace']={'available':False,'reason':'REQUEST_BOUND'}
                path=output/'candidates'/f'{number}-{index}.json'
                write_json(path,record)
                row={'block':number,'transaction_index':index,'transaction_hash':tx.get('hash'),'accepted':not reasons,'reasons':reasons,'record':bind(path,root)}
                inspected.append(row)
                if not reasons: accepted.append(row)
                if stop: break
            blocks.append({'number':number,'accepted':admitted,'status':'INSPECTED',**block_binding})
    except RequestBoundReached:
        stop='REQUEST_BOUND_REACHED'
    summary={'study':STUDY,'status':'COMPLETE' if len(accepted)==preregistration['target_count'] else 'INCOMPLETE',
        'accepted_count':len(accepted),'target_count':preregistration['target_count'],'accepted':accepted,
        'candidates':inspected,'blocks':blocks,'stop_reason':stop or 'TARGET_REACHED_OR_FIXED_BLOCKS_EXHAUSTED',
        'chain_evidence':bind(output/'chain.json',root),'outbound_logical_requests':request_count,
        'max_requests':MAX_REQUESTS,'accounting':meter.summary(),'record_format':'Parsed JSON RPC envelopes; not HTTP octet bytes; RPC error messages redacted',
        'heldout_used':False,'detector_used_for_selection':False,'stage2_executed':False}
    write_json(output/'summary.json',summary)
    return summary


def run_live(root=ROOT, live=False):
    if not live: raise ValueError('Explicit --live flag required before credential loading or RPC dispatch')
    root=Path(root).resolve()
    prereg_path=root/'reports/cohort_rebuild_v2/benign_control_preregistration.json'
    prereg=json.loads(prereg_path.read_text())
    if (prereg.get('study')!=STUDY or prereg.get('target_count')!=32 or prereg.get('block_numbers')!=BLOCKS
        or prereg.get('chain')!='eth' or prereg.get('chain_id')!=1):
        raise ValueError('Preregistered control population mismatch')
    output=root/'reports/cohort_rebuild_v2/benign_controls'
    if output.exists() and any(output.iterdir()): raise ValueError('Control output already exists; refusing silent redispatch')
    from dotenv import dotenv_values
    values=dotenv_values(root/'.env')
    endpoint=os.getenv('DRPC_RPC_URL') or values.get('DRPC_RPC_URL') or ''
    key=os.getenv('DRPC_API_KEY') or values.get('DRPC_API_KEY') or ''
    endpoint=endpoint.replace('{chain}','eth').replace('{api_key}',quote(key,safe=''))
    if not endpoint.startswith('https://') or '{' in endpoint: raise ValueError('HTTPS archive endpoint configuration required')
    meter=MeteredRPC(endpoint,root/'data/research/spend_ledger.json',max_requests=MAX_REQUESTS)
    summary=acquire(meter,prereg,output,root)
    summary['preregistration']=bind(prereg_path,root)
    write_json(output/'summary.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    try:
        result=run_live(live=args.live)
        print(json.dumps({'status':result['status'],'accepted':result['accepted_count'],'requests':result['outbound_logical_requests']}))
    except (ValueError,RuntimeError,OSError) as error:
        print('Control acquisition failed:',type(error).__name__)
        sys.exit(1)
