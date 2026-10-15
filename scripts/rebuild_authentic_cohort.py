"""Acquire genuine incident leads and RPC evidence; publish only admitted rows.

Downloads are never executed. Source titles and transaction references are leads,
not independent vulnerability annotations. RPC credentials never enter reports.
"""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit, quote, unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault('readline', None)
from benchmark.research_protocol import bind, read_bound, write_json, identity, admit, make_split, sha
from benchmark.evidence_manifest import CHAIN_IDS

BASE = ROOT / 'reports/cohort_rebuild_v2'
NETWORKS = {'eth':'ethereum','bsc':'bsc','polygon':'polygon','arbitrum':'arbitrum','optimism':'optimism',
            'avalanche':'avalanche','base':'base','zksync':'zksync','gnosis':'gnosis','fantom':'fantom'}
EXPLORERS = {'etherscan.io':'eth','bscscan.com':'bsc','polygonscan.com':'polygon',
             'arbiscan.io':'arbitrum','optimistic.etherscan.io':'optimism','basescan.org':'base',
             'snowtrace.io':'avalanche','explorer.zksync.io':'zksync','gnosisscan.io':'gnosis',
             'ftmscan.com':'fantom'}


def drpc_url(authorized, chain):
    parsed = urlsplit(authorized)
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or parsed.hostname != 'lb.drpc.live' or len(parts) != 2 or not parts[1]:
        raise ValueError('Configured endpoint does not permit safe network routing')
    return 'https://lb.drpc.live/' + NETWORKS[chain] + '/' + quote(unquote(parts[1]), safe='')


def extract_candidates(text, url):
    output, seen = [], set()
    for section in re.split(r'(?m)^### (?=\d{8})', text)[1:]:
        title = section.splitlines()[0].strip()
        links = sorted(set(u.rstrip(').,;') for u in re.findall(r'https://[^\s<>\]\"\)]+', section)))
        for link in links:
            parsed = urlsplit(link)
            chain = EXPLORERS.get(parsed.hostname)
            match = re.fullmatch(r'/tx/(0x[0-9a-fA-F]{64})/?', parsed.path)
            if not chain and parsed.hostname == 'blockscout.com':
                match = re.fullmatch(r'/xdai/mainnet/tx/(0x[0-9a-fA-F]{64})/?', parsed.path)
                chain = 'gnosis' if match else None
            if not chain or not match:
                continue
            tx = match[1].lower()
            if (chain,tx) in seen:
                continue
            seen.add((chain,tx))
            output.append({'txn_hash':tx,'chain':chain,'incident_title':title,
                'incident_id':'DeFiHackLabs:'+re.sub(r'[^A-Za-z0-9]+','-',title).strip('-'),
                'index_url':url,'reference_links':links,'membership':'ADDITIONAL-UNADJUDICATED-TRANSACTION-REFERENCE',
                'role':'NOT-YET-ESTABLISHED; may include funding/recovery references'})
    return output


def import_poc_leads(existing, imported):
    rows = list(existing)
    seen = {identity(r) for r in rows}
    for raw in imported:
        tx, chain = raw.get('candidate_tx_hash','').lower(), raw.get('candidate_chain')
        if not re.fullmatch('0x[a-f0-9]{64}',tx) or chain not in CHAIN_IDS or chain+':'+tx in seen:
            continue
        rows.append({'txn_hash':tx,'chain':chain,'incident_title':raw.get('title',''),
            'incident_id':'DeFiHackLabs:'+str(raw.get('incident_id') or tx),
            'index_url':raw.get('source'),'reference_links':[],
            'membership':'ADDITIONAL-UNADJUDICATED-TRANSACTION-REFERENCE',
            'role':'IMPORTED-POC-LEAD-NOT-ADJUDICATED','sources':[],'legacy_ground_truth':[]})
        seen.add(chain+':'+tx)
    return rows


def expand():
    from scripts import hunt_claim_provenance as http
    http.OUT = BASE
    rows = json.loads((BASE/'candidate_pool.json').read_text())
    imported = []
    inputs = []
    for name in ('defihacklabs_github_candidates.csv','defihacklabs_candidate_expansion.csv'):
        path = ROOT/'benchmark/imported'/name
        imported += list(csv.DictReader(path.open(encoding='utf-8-sig')))
        inputs.append(bind(path,ROOT))
    rows = import_poc_leads(rows,imported)
    write_json(BASE/'candidate_pool.json',rows)
    links = sorted({r.get('index_url','').replace('https://github.com/','https://raw.githubusercontent.com/').replace('/blob/','/')
                    for r in rows if str(r.get('index_url','')).startswith('https://github.com/SunWeb3Sec/DeFiHackLabs/blob/')})
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, future in enumerate(as_completed([pool.submit(http.fetch,u) for u in links]),1):
            results.append(future.result())
            if i%100==0:
                print('Public PoC evidence cached',i,'of',len(links),flush=True)
    write_json(BASE/'poc_sources.json',{'inputs':inputs,'sources':results,'candidate_count':len(rows)})
    print('Expanded candidate pool',len(rows),'PoC artifacts',len(results),flush=True)


def identity_observation(row, chain_id, payload):
    by_id = {item.get('id'):item for item in payload} if isinstance(payload,list) else {}
    a, b = by_id.get(1,{}).get('result'), by_id.get(2,{}).get('result')
    try:
        good = bool(chain_id == CHAIN_IDS[row['chain']] and a and b
            and a.get('hash','').lower() == row['txn_hash'] and b.get('transactionHash','').lower() == row['txn_hash']
            and a.get('blockHash') == b.get('blockHash') and a.get('blockHash')
            and int(a['chainId'],16) == chain_id)
    except (KeyError, TypeError, ValueError):
        good = False
    return {'mode':'live-rpc','txn_hash':row['txn_hash'],'chain':row['chain'],'chain_id':chain_id,
            'provider':'authorized-dRPC-'+row['chain'], 'observed_at':datetime.now(timezone.utc).isoformat(),
            'transaction':a,'receipt':b,'raw_responses':payload,'identity_receipt_match':good,
            'scope':'One authenticated RPC provider; no independent label or second-node attestation'}


def cached_meta():
    records = {}
    for folder in (ROOT/'reports/provenance_hunt/http', BASE/'http'):
        for path in folder.glob('*.json') if folder.exists() else []:
            item = json.loads(path.read_text(encoding='utf-8-sig'))
            if item.get('file') and item.get('http_status') == 200:
                raw = (ROOT/item['file']).read_bytes()
                if sha(raw) != item['sha256']:
                    raise ValueError('Cached source digest mismatch')
                records[item['url']] = item
    return records


def body(meta):
    raw = (ROOT/meta['file']).read_bytes()
    if sha(raw) != meta['sha256']:
        raise ValueError('Source digest mismatch')
    return (gzip.decompress(raw) if meta.get('compressed') else raw).decode('utf-8',errors='replace')


def acquire():
    from scripts import hunt_claim_provenance as http
    http.OUT = BASE
    urls = [
        'https://api.llama.fi/hacks',
        'https://raw.githubusercontent.com/slowmist/SlowMist-Hacked/master/README.md',
        'https://raw.githubusercontent.com/slowmist/SlowMist-Hacked/master/README_EN.md',
        'https://hacked.slowmist.io/en/statistics/?c=all&d=all',
        'https://www.certik.com/zh-CN/blog/euler-finance-incident-analysis',
        'https://www.certik.com/blog/inverse-finance-incident-analysis',
        'https://www.halborn.com/blog/post/explained-the-grim-finance-hack-december-2021',
        'https://slowmist.medium.com/analysis-of-the-grim-finance-hack-bc440108b069',
        'https://swcregistry.io/docs/SWC-107/',
        'https://drpc.org/docs/gettingstarted/firstrequest',
    ]
    previous = cached_meta()
    urls += ['https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/README.md']
    urls += [f'https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/past/{y}/README.md' for y in range(2021,2027)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(http.fetch, urls))
    write_json(BASE/'acquisition_sources.json',fetched)
    metas = cached_meta()
    manifest = json.loads((ROOT/'reports/canonical_history/manifest.json').read_text())
    snapshot = next(a for a in manifest['artifacts'] if a['category']=='requested-231-row-snapshot')
    original = list(csv.DictReader(io.StringIO((ROOT/snapshot['cache']).read_text(encoding='utf-8-sig'))))
    extra = json.loads((ROOT/'reports/provenance_hunt/new_candidates.json').read_text())['rows']
    rows = [dict(r, membership='FROZEN-231', incident_id='legacy:'+r['chain']+':'+r['txn_hash']) for r in original]
    rows += [dict(r,membership='ORIGINAL-15-CANDIDATES',incident_id='candidate:'+r['title']) for r in extra]
    seen = {identity(r) for r in rows}
    for url, artifact in sorted(metas.items()):
        if '/SunWeb3Sec/DeFiHackLabs/' not in url:
            continue
        for row in extract_candidates(body(artifact),url):
            if identity(row) not in seen:
                row['index_artifact'] = bind(ROOT/artifact['file'],ROOT)
                rows.append(row)
                seen.add(identity(row))
    gt_by_hash = defaultdict(list)
    for artifact in manifest['artifacts']:
        if artifact['category'] == 'ground-truth-original':
            gt = json.loads((ROOT/artifact['cache']).read_text(encoding='utf-8-sig'))
            for tx in gt.get('transaction_hash',[]):
                gt_by_hash[tx.lower()].append(bind(ROOT/artifact['cache'],ROOT))
    pairs = {r['txn_hash']:r for r in json.loads((ROOT/'reports/provenance_hunt/reviewed_source_pairs.json').read_text())}
    for row in rows:
        row['legacy_labels'] = {k:row.pop(k) for k in ('vuln_type','swc_registry_classification','dasp_classification','uncategorized') if k in row}
        row['legacy_ground_truth'] = gt_by_hash[row['txn_hash'].lower()]
        row['sources'] = []
        for source in pairs.get(row['txn_hash'],{}).get('sources',[]):
            row['sources'].append({'publisher_id':source['publisher'],'independence_group':source['publisher'],
                'url':source['url'],'artifact':bind(ROOT/source['artifact'],ROOT),
                'review_status':'INDEPENDENT_SECURITY_PUBLISHER_CONFIRMED',
                'independence_basis':pairs[row['txn_hash']]['independence_basis'],
                'identity_basis':source.get('hash_links',[])})
    write_json(BASE/'candidate_pool.json',rows)
    corpus_notes = []
    for source in fetched:
        if source.get('http_status') != 200:
            corpus_notes.append({'url':source['url'],'status':'FETCH_FAILED_OR_UNAVAILABLE','http_status':source.get('http_status')})
        elif source['url']=='https://api.llama.fi/hacks':
            data = json.loads(body(source))
            corpus_notes.append({'url':source['url'],'incident_entries':len(data),'status':'INCIDENT_METADATA_NOT_TRANSACTION_LABELS',
                                 'note':'No invented hashes or title-derived vulnerability labels imported'})
    write_json(BASE/'corpus_notes.json',corpus_notes)
    print('Candidate pool',len(rows),dict(Counter(r['membership'] for r in rows)),flush=True)
    return rows


def acquire_rpc():
    from dotenv import dotenv_values
    from scripts.replay_historical_opcodes import MeteredRPC
    authorized = dotenv_values(ROOT/'.env').get('DRPC_RPC_URL')
    if not authorized:
        raise ValueError('DRPC_RPC_URL absent; no calls dispatched')
    rows = json.loads((BASE/'candidate_pool.json').read_text())
    # Every historical/candidate identity is queried. Extra unadjudicated leads
    # fail cheap provenance gates first; twelve per new chain establish whether
    # real historical identity acquisition is possible there, without blind replay.
    selected = [r for r in rows if r['membership']!='ADDITIONAL-UNADJUDICATED-TRANSACTION-REFERENCE']
    for chain in ('fantom','gnosis'):
        selected += [r for r in rows if r['membership']=='ADDITIONAL-UNADJUDICATED-TRANSACTION-REFERENCE'
                     and r['chain']==chain][:12]
    by_chain = defaultdict(list)
    for row in selected:
        by_chain[row['chain']].append(row)
    summaries = []
    for chain, records in sorted(by_chain.items()):
        meter = MeteredRPC(drpc_url(authorized,chain),ROOT/'data/research/spend_ledger.json',max_requests=1200)
        try:
            actual = int(meter.rpc('eth_chainId',[]),16)
            if actual != CHAIN_IDS[chain]:
                raise ValueError('Endpoint returned wrong chain')
        except Exception as error:
            summaries.append({'chain':chain,'status':'CHAIN_UNAVAILABLE','error_type':type(error).__name__,**meter.summary()})
            print('Chain unavailable',chain,type(error).__name__,flush=True)
            continue
        def capture(row):
            path = BASE/'rpc'/chain/(row['txn_hash']+'.json')
            if path.exists():
                return
            try:
                result = meter.forward([{'jsonrpc':'2.0','id':1,'method':'eth_getTransactionByHash','params':[row['txn_hash']]},
                                        {'jsonrpc':'2.0','id':2,'method':'eth_getTransactionReceipt','params':[row['txn_hash']]}])
                observed = identity_observation(row,actual,result)
            except Exception as error:
                observed = {'txn_hash':row['txn_hash'],'chain':chain,'mode':'live-rpc',
                            'error_type':type(error).__name__,'identity_receipt_match':False,
                            'observed_at':datetime.now(timezone.utc).isoformat()}
            write_json(path, observed)
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(capture,records))
        finally:
            summary = dict(chain=chain,status='QUERIED',selected_rows=len(records),**meter.summary())
            summaries.append(summary)
            write_json(BASE/'rpc_accounting.json',summaries)
        print('RPC chain completed',chain,len(records),'requests',meter.count,flush=True)
    write_json(BASE/'rpc_accounting.json',summaries)


def audit():
    rows = json.loads((BASE/'candidate_pool.json').read_text())
    decisions = []
    accepted = []
    for row in rows:
        record = dict(row)
        path = BASE/'rpc'/row['chain']/(row['txn_hash']+'.json')
        if path.exists():
            record['rpc'] = bind(path,ROOT)
        annotation = BASE/'annotations'/(row['txn_hash']+'.json')
        if annotation.exists():
            record['annotation_record'] = bind(annotation,ROOT)
        decision = admit(record,ROOT)
        decisions.append(dict(decision,membership=row['membership']))
        if decision['accepted']:
            accepted.append(record)
    write_json(BASE/'records.json',rows)
    write_json(BASE/'admitted_records.json',accepted)
    write_json(BASE/'row_decisions.json',{'rows':decisions,'input_rows':len(rows),
        'accepted_rows':len(accepted),'by_membership':{k:{'audited':sum(d['membership']==k for d in decisions),
            'accepted':sum(d['membership']==k and d['accepted'] for d in decisions)} for k in sorted({r['membership'] for r in rows})},
        'missing_counts':dict(Counter(reason for d in decisions for reason in d['reasons']))})
    print('Admission audit',len(accepted),'accepted of',len(rows),flush=True)
    return accepted


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquire',action='store_true')
    parser.add_argument('--rpc',action='store_true')
    parser.add_argument('--expand',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    if args.acquire:
        acquire()
    if args.rpc:
        acquire_rpc()
    if args.expand:
        expand()
    if args.audit:
        audit()
