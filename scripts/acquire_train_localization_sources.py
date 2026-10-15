"""Acquire train-only source identity evidence, without altering frozen labels.

Uses public Sourcify v2 GET requests only. No prediction files or heldout
partition are opened. Cached responses and every failed attempt are retained.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

sys.modules['readline'] = None
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.research_protocol import load_train, read_bound, bind, source_text
from eth_utils import keccak

OUT = ROOT / 'reports/cohort_rebuild_v2/localization_sources'
CANDIDATES = {
    'reviewed:Euler Finance': ['0xbb0d4bb654a21054af95456a3b29c63e8d1f4c0a','0x3297c8db9360f87a7f7826f52a4fa143988931a6','0x29daddfda3442693c21a50351a2b4820ddbbff79','0x42ec0eb1d2746a9f2739d7501c5d5608bde9ee89'],
    'reviewed:Revest Finance': ['0x2320a28f52334d62622cc2eafa15de55f9987ed9','0xa81bd16aa6f6b25e66965a2f842e9c806c0aa11f','0x226124e83868812d3dae87eb3c5f28047e1070b7','0xe952bda8c06481506e4731c4f54ced2d4ab81659'],
}

def abi_signature(entry):
    def typ(item):
        value = item['type']
        if value.startswith('tuple'):
            return '(' + ','.join(typ(x) for x in item['components']) + ')' + value[5:]
        return value
    return entry['name'] + '(' + ','.join(typ(x) for x in entry['inputs']) + ')'

def verified_contract(data, address, historical_code):
    code = data.get('runtimeBytecode', {}).get('onchainBytecode')
    return bool(data.get('address', '').lower() == address.lower()
                and str(data.get('chainId')) == '1'
                and data.get('runtimeMatch') in ('exact_match', 'match')
                and isinstance(code, str) and len(code) > 2
                and code.lower() == historical_code.lower())

def trace_matches(tree, address, selector):
    found = []
    def visit(node, owner=None, path=()):
        kind = node.get('type', 'CALL').upper()
        code_address = node.get('to', '').lower()
        storage = owner if kind in ('DELEGATECALL', 'CALLCODE') else code_address
        if code_address == address.lower() and node.get('input', '')[:10].lower() == selector.lower():
            found.append({'trace_path':list(path), 'code_address':code_address,
                          'storage_address':storage, 'call_type':kind,
                          'selector':selector, 'error':node.get('error')})
        for i, child in enumerate(node.get('calls', [])):
            visit(child, storage, path + (i,))
    visit(tree)
    return found

class Fetcher:
    def __init__(self, live, retry_network=False):
        self.live = live
        self.retry_network = retry_network
        self.previous = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT/'http').glob('*.attempt1.json'))]
        self.requests = 0
        self.attempts = []
    def get(self, url):
        key = hashlib.sha256(url.encode('utf-8')).hexdigest()
        body = OUT / 'http' / (key + '.body')
        meta = OUT / 'http' / (key + '.json')
        if body.exists() and meta.exists():
            record = json.loads(meta.read_text(encoding='utf-8'))
            if hashlib.sha256(body.read_bytes()).hexdigest() != record['body_sha256']:
                raise ValueError('Cached response digest mismatch')
            if (record['status'] != 'NETWORK_ERROR' or not self.retry_network
                    or body.with_suffix('.attempt1.body').exists()):
                self.attempts.append(dict(record, reused_cache=True))
                return body.read_bytes() if record['status'] == 200 else None

            old_body = body.with_suffix('.attempt1.body')
            old_meta = meta.with_suffix('.attempt1.json')
            if not old_body.exists():
                old_body.write_bytes(body.read_bytes())
                old_meta.write_text(json.dumps(dict(record, body=old_body.relative_to(ROOT).as_posix()),indent=2)+'\n',encoding='utf-8')
        if not self.live:
            self.attempts.append({'url':url,'status':'NO_CACHE'})
            return None
        # Count preserved original failures plus final responses across invocations.
        # Only one retry of a network failure is allowed, so no attempt is overwritten.
        if (self.requests + len(self.previous) >= 19
                or 1 + len(list((OUT/'http').glob('*.json'))) >= 20):
            raise ValueError('20-request public HTTP budget exhausted')
        self.requests += 1
        try:
            request = urllib.request.Request(url, headers={'User-Agent':'FaultSeeker-research/1.0','Accept':'application/json'})
            with urllib.request.urlopen(request, timeout=45) as response:
                raw, status = response.read(), response.status
        except urllib.error.HTTPError as error:
            raw, status = error.read(), error.code
        except (OSError, TimeoutError) as error:
            raw, status = str(error).encode('utf-8'), 'NETWORK_ERROR'
        body.parent.mkdir(parents=True, exist_ok=True)
        body.write_bytes(raw)
        record = {'url':url,'status':status,'body_sha256':hashlib.sha256(raw).hexdigest(),
                  'body':body.relative_to(ROOT).as_posix()}
        meta.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        self.attempts.append(record)
        return raw if status == 200 else None

def run(live=False, retry_network=False):
    split = json.loads((ROOT/'benchmark/eval_split.json').read_text(encoding='utf-8'))
    rows = load_train(split,ROOT)
    fetcher = Fetcher(live,retry_network)
    fetcher.get('https://docs.sourcify.dev/docs/api/')
    cases = []
    for row in rows:
        if row['incident_id'] not in CANDIDATES:
            continue
        gt = json.loads(read_bound(row['ground_truth'],ROOT))
        prestate = json.loads(gzip.decompress(read_bound(row['prestate'],ROOT)))['response']['result']
        tree = json.loads(gzip.decompress(read_bound(row['trace'],ROOT)))['raw_trace']['call']
        names = {x['name'] for x in gt['source_supported_functions']}
        opcode_path=ROOT/'reports/cohort_rebuild_v2/opcodes'/(row['txn_hash']+'.json.gz')
        opcode=json.loads(gzip.decompress(opcode_path.read_bytes()))
        if opcode.get('transaction_hash') != row['txn_hash'] or opcode.get('chain') != row['chain'] or opcode.get('normalization',{}).get('normalization_complete') is not True:
            raise ValueError('Opcode historical identity/normalization not verified')
        case = {'identity':row['chain']+':'+row['txn_hash'],'incident':row['incident_id'],
                'train_ground_truth':row['ground_truth'],'trace':row['trace'],'prestate':row['prestate'],
                'opcode_capture':bind(opcode_path,ROOT),'opcode_normalization_complete':True,
                'root_cause_citations':gt['source_supported_functions'], 'contracts':[], 'function_evidence':[],
                'line_targets':[], 'line_status':'UNAVAILABLE: function declarations do not establish vulnerable source lines'}
        # Both publishers are attributed even if only one names a function.
        annotation = json.loads(read_bound(row['annotation_record'], ROOT))
        case['publisher_mechanism_observations'] = annotation.get('independent_observations',[])
        for address in CANDIDATES[row['incident_id']]:
            # Candidate addresses are actual trace code destinations, never predictions.
            def destinations(node):
                return {node.get('to','').lower()} | set().union(*(destinations(c) for c in node.get('calls',[])))
            if address not in destinations(tree):
                raise ValueError('Candidate absent from historical trace')
            url = 'https://sourcify.dev/server/v2/contract/1/'+address+'?fields=all'
            raw = fetcher.get(url)
            contract = {'address':address,'url':url,'historical_code_present':bool(prestate.get(address,{}).get('code'))}
            if raw is None:
                contract['status']='SOURCE_RESPONSE_UNAVAILABLE';case['contracts'].append(contract);continue
            data = json.loads(raw.decode('utf-8'))
            code = prestate.get(address,{}).get('code','')
            verified = verified_contract(data,address,code)
            contract.update(status='HISTORICAL_RUNTIME_MATCH' if verified else 'HISTORICAL_RUNTIME_NOT_VERIFIED',
                            runtime_match=data.get('runtimeMatch'),response=bind(OUT/'http'/(hashlib.sha256(url.encode()).hexdigest()+'.body'),ROOT),
                            historical_code_sha256=hashlib.sha256(code.encode('ascii')).hexdigest())
            case['contracts'].append(contract)
            if not verified:
                continue
            for entry in data.get('abi') or []:
                if entry.get('type') != 'function' or entry.get('name') not in names:
                    continue
                signature = abi_signature(entry)
                selector = '0x'+keccak(text=signature)[:4].hex()
                matches = trace_matches(tree,address,selector)
                if matches:
                    for match in matches:
                        call_id='0'+''.join('.'+str(i) for i in match['trace_path'])
                        events=[e for e in opcode['normalization']['storage_events'] if e.get('call_id')==call_id]
                        match['opcode_frame_call_id']=call_id
                        match['opcode_storage_event_count']=len(events)
                        match['opcode_storage_owners']=sorted({e['address'] for e in events})
                        if any(e['address'].lower()!=match['storage_address'] for e in events):
                            raise ValueError('Opcode/call-tree storage owner mismatch')
                    case['function_evidence'].append({'name':entry['name'],'signature':signature,'selector':selector,
                        'code_address':address,'abi_response':contract['response'],'executed_calls':matches,
                        'verified_compilation':data.get('compilation'),
                        'verified_source_paths':sorted(data.get('sources',{})),
                        'status':'PUBLISHER_NAME_AND_HISTORICAL_BYTECODE_VERIFIED_ABI_AND_TRACE_SELECTOR',
                        'ground_truth_mutated':False})
        case['status']='FUNCTION_IDENTITY_VERIFIED' if case['function_evidence'] else 'FUNCTION_IDENTITY_UNAVAILABLE'
        cases.append(case)
    report={'schema':1,'scope':'Frozen TRAIN only; source identity acquisition; no scoring and no ground truth mutation',
            'documentation_url':'https://docs.sourcify.dev/docs/api/','external_documentation_requests':1,
            'new_http_requests_this_run':fetcher.requests,'prior_failed_attempts':fetcher.previous,'total_session_public_request_attempts_including_external_documentation':1+len(list((OUT/'http').glob('*.json'))),
            'requests':fetcher.attempts,'cases':cases,
            'limitations':['Sourcify attestation is not an independent rebuild of the compiler output.',
                           'No line targets inferred from function names, ABI, or model predictions.',
                           'Candidate search is bounded, not exhaustive; failed lookup is not evidence of absence.']}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'evidence.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'requests':fetcher.requests,'cases':[{k:c[k] for k in ('incident','status','function_evidence')} for c in cases]},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--retry-network',action='store_true');args=parser.parse_args();run(args.live,args.retry_network)
