"""Cache public leads for each exact cohort identity; never auto-adjudicate them.

Downloaded pages/code are untrusted data and are never executed. Distinct hosts,
hash hits, PoC mirrors and explorer pages do not establish research independence.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
from urllib.error import HTTPError
from urllib.parse import urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/provenance_hunt'
HASH = re.compile(r'0x[0-9a-fA-F]{64}(?![0-9a-fA-F])')
CHALLENGES = ('just a moment', 'enable javascript and cookies', 'verify you are human',
              'captcha', 'access denied', 'checking your browser')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')


def ethereum_transaction_link(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('etherscan.io', 'www.etherscan.io'):
        return None
    match = re.fullmatch(r'/tx/(0x[0-9a-fA-F]{64})', parsed.path)
    return match[1].lower() if match else None


def inspect_artifact(tx, artifact):
    path = Path(artifact['file'])
    if not path.is_absolute():
        path = ROOT / path
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != artifact['sha256']:
        raise ValueError('Source digest mismatch')
    if artifact.get('compressed'):
        data = gzip.decompress(data)
    text = data.decode('utf-8', errors='replace').lower()
    hit = tx.lower() in text
    challenge = any(marker in text[:30000] for marker in CHALLENGES)
    missing_identity = any(marker in text for marker in (
        'unable to locate this transaction hash', 'transaction hash not found',
        'transaction not found', 'no matching entries'))
    derived = any(marker in text for marker in (
        'analysis adapted from defihacklabs', 'source & credit', 'source: defihacklabs'))
    return {'body_hash_match': hit, 'challenge_detected': challenge,
        'identity_not_found_marker': missing_identity,
        'usable_identity_reference': hit and not challenge and not missing_identity and artifact.get('http_status') == 200,
        'explicit_derivative_marker': derived,
        'independence': 'NOT_ESTABLISHED', 'incident_label': 'NOT_ADJUDICATED'}


def public_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443)):
        raise ValueError('Only public HTTPS sources are allowed')
    for addr in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[4][0]).is_global:
            raise ValueError('Nonpublic source address')
    return url


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    identity = hashlib.sha256(url.encode()).hexdigest()
    metadata = OUT / 'http' / (identity + '.json')
    if metadata.is_file():
        record = json.loads(metadata.read_text(encoding='utf-8'))
        if record.get('file'):
            inspect_artifact('', record)  # Verify cached bytes before reuse.
        return record
    record = {'url': url, 'request_kind': 'public-unauthenticated-http', 'paid_calls': 0}
    try:
        public_url(url)
        request = Request(url, headers={'User-Agent': 'FaultSeeker-Provenance/1.0'})
        try:
            response = build_opener(PublicRedirect).open(request, timeout=12)
        except HTTPError as error:
            response = error
        with response:
            data = response.read(4_000_001)
            if len(data) > 4_000_000:
                raise ValueError('Source exceeds four MB bound; not cached as complete')
            record.update(http_status=response.code, final_url=response.url,
                          content_type=response.headers.get('Content-Type'))
        path = OUT / 'http' / (identity + '.gz')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(data, mtime=0))
        record.update(file=str(path.relative_to(ROOT)).replace('\\', '/'), compressed=True,
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      body_sha256=hashlib.sha256(data).hexdigest(), body_bytes=len(data))
    except Exception as error:
        # Do not record arbitrary exception text or authentication material.
        record['error_type'] = type(error).__name__
    write(metadata, record)
    return record


def source_urls():
    rows = list(csv.DictReader((ROOT / 'benchmark/benchmark_classification_fixed.csv').open(
        encoding='utf-8-sig')))
    urls = set()
    for row in rows:
        try:
            values = json.loads(row.get('analysis') or '[]')
        except ValueError:
            values = []
        if isinstance(values, list):
            urls.update(u for u in values if isinstance(u, str) and u.startswith('https://'))
    # Search-result headings, not URLs inside untrusted snippets, select leads.
    for path in sorted((OUT / 'search').glob('*.json')):
        search = json.loads(path.read_text(encoding='utf-8'))
        urls.update(re.findall(r'^.*?\((https://[^\s)]+)\)\s*$', search['result'], re.M))
    new_path = OUT / 'new_candidates.json'
    if new_path.is_file():
        for candidate in json.loads(new_path.read_text(encoding='utf-8'))['rows']:
            urls.update(url for url in candidate['reference_links'] if url.startswith('https://'))
    urls.update([
        'https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/README.md',
        'https://raw.githubusercontent.com/Autosaida/DeFiHackAnalysis/master/README.md',
        'https://hacked.slowmist.io/',
        'https://mixbytes.io/blog/foundry-for-studying-hacks',
        'https://learnblockchain.cn/article/5462',
    ])
    # New corpus candidates are found in the public historical indexes, not
    # generated by changing source hashes or inventing rows.
    for year in range(2020, 2026):
        urls.add(f'https://raw.githubusercontent.com/SunWeb3Sec/DeFiHackLabs/main/past/{year}/README.md')
    return rows, sorted(urls)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--verify-ethereum', action='store_true')
    args = parser.parse_args()
    rows, urls = source_urls()
    if args.verify_ethereum:
        import os
        import sys
        from dotenv import load_dotenv
        sys.path.insert(0, str(ROOT))
        from scripts.replay_historical_opcodes import MeteredRPC
        load_dotenv(ROOT / '.env')
        url = os.environ.get('DRPC_RPC_URL')
        if not url:
            raise SystemExit('DRPC_RPC_URL is required; no request dispatched')
        meter = MeteredRPC(url, ROOT / 'data/research/spend_ledger.json', max_requests=400)
        if int(meter.rpc('eth_chainId', []), 16) != 1:
            raise SystemExit('Configured endpoint is not Ethereum; refusing identity queries')
        new_path = OUT / 'new_candidates.json'
        extra = json.loads(new_path.read_text(encoding='utf-8'))['rows'] if new_path.is_file() else []
        identities = sorted({r['txn_hash'].lower() for r in rows + extra if r['chain'] == 'eth'})

        def verify(tx):
            path = OUT / 'ethereum' / (tx + '.json')
            if path.exists():
                return
            result = {'txn_hash': tx, 'chain': 'eth', 'provider': 'configured-dRPC',
                      'scope': 'Single-provider identity and receipt; no incident-label attestation'}
            try:
                response = meter.forward([
                    {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getTransactionByHash', 'params': [tx]},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'eth_getTransactionReceipt', 'params': [tx]}])
                by_id = {r['id']: r for r in response}
                result.update(transaction=by_id[1], receipt=by_id[2])
                a, b = by_id[1].get('result'), by_id[2].get('result')
                result['identity_receipt_match'] = bool(a and b and a.get('hash', '').lower() == tx
                    and b.get('transactionHash', '').lower() == tx and a.get('blockHash') == b.get('blockHash'))
                result['rpc_null_result'] = not by_id[1].get('error') and not by_id[2].get('error') and a is None and b is None
            except Exception as error:
                result['error_type'] = type(error).__name__
            write(path, result)

        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(verify, identities))
        finally:
            import uuid
            summary = meter.summary()
            write(OUT / 'ethereum_request_runs' / (uuid.uuid4().hex + '.json'), summary)
            write(OUT / 'ethereum_requests.json', summary)
        print(json.dumps(meter.summary()))
        return
    if args.fetch:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(fetch, url) for url in urls]
            for index, future in enumerate(as_completed(futures), 1):
                future.result()
                if index % 25 == 0:
                    print(f'Public source requests completed: {index}/{len(urls)}', flush=True)
    artifacts = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT / 'http').glob('*.json'))]
    decisions = []
    identity_index = {row['txn_hash'].lower(): [] for row in rows}
    # Decode each cached page once; only inspect identities actually present.
    # The former row-by-artifact loop repeated 27MB of compressed IO 231 times.
    for artifact in artifacts:
        if not artifact.get('file'):
            continue
        data = (ROOT / artifact['file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != artifact['sha256']:
            raise ValueError('Source digest mismatch')
        if artifact.get('compressed'):
            data = gzip.decompress(data)
        present = {tx.lower() for tx in HASH.findall(data.decode('utf-8', errors='replace'))}
        for tx in present.intersection(identity_index):
            identity_index[tx].append({**artifact, **inspect_artifact(tx, artifact)})
    search_batches = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((OUT / 'search').glob('batch_*.json'))]
    for ordinal, row in enumerate(rows, 1):
        matches = identity_index.get(row['txn_hash'].lower(), [])
        batches = [i for i, batch in enumerate(search_batches) if any(
            query['ordinal'] == ordinal and query['txn_hash'] == row['txn_hash']
            for query in batch['queries'])]
        decisions.append({'ordinal': ordinal, 'txn_hash': row['txn_hash'], 'chain': row['chain'],
            'exact_hash_search_recorded': bool(batches), 'matching_artifacts': matches,
            'independent_corroboration': 'NOT_ESTABLISHED', 'cohort_accepted': False,
            'reason': 'Source identity hits require research-independence and label adjudication; existing full provenance gate still applies.'})
    report = {'rows': decisions, 'input_rows': len(rows), 'searched_rows': sum(
        r['exact_hash_search_recorded'] for r in decisions), 'url_count': len(urls),
        'cached_request_records': len(artifacts), 'paid_provider_calls': 0,
        'scope': 'Public exact-hash search and source-lead caching; not an annotation or authenticity attestation'}
    write(OUT / 'hunt.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
