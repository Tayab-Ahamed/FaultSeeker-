"""Bounded explorer retrieval with recorded challenge recovery attempts.

A browser TLS transport requires a configured curl-impersonate executable.
Success means an actual non-challenge 2xx response, never a fabricated page.
"""
import hashlib
import os
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


def challenged(status, body):
    text = body.lower()
    return any(marker in text for marker in ('cf-chl-', 'just a moment...', 'checking your browser',
                                               'cloudflare ray id', 'attention required! | cloudflare'))


def _transport(url, strategy):
    if strategy == 'browser':
        binary = os.getenv('CURL_IMPERSONATE_BINARY')
        if not binary or not os.path.isfile(binary):
            raise RuntimeError('PENDING-CREDENTIALS: CURL_IMPERSONATE_BINARY is required')
        result = subprocess.run([binary, '--silent', '--show-error', '--location', '--max-time', '30',
                                 '--write-out', '\n%{http_code}', url],
                                capture_output=True, text=True, timeout=35)
        if result.returncode:
            raise RuntimeError('browser TLS transport failed')
        body, status = result.stdout.rsplit('\n', 1)
        return int(status), body
    if strategy != 'standard':
        raise ValueError('Unknown retrieval strategy')
    request = Request(url, headers={'User-Agent': 'FaultSeeker/1.0'})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except HTTPError as error:
        return error.code, error.read().decode('utf-8', errors='replace')


class RecoveryClient:
    def __init__(self, transport=None, strategies=None):
        self.transport = transport or _transport
        self.strategies = list(strategies or ['standard'] + (['browser'] if os.getenv('CURL_IMPERSONATE_BINARY') else []))

    def fetch(self, url):
        if urlparse(url).scheme not in {'https', 'http'}:
            raise ValueError('Only HTTP(S) acquisition is supported')
        attempts, was_challenged = [], False
        body = ''
        success = False
        for strategy in self.strategies:
            started = time.perf_counter()
            try:
                status, body = self.transport(url, strategy)
                is_challenge = challenged(status, body)
                was_challenged |= is_challenge
                success = 200 <= status < 300 and bool(body.strip()) and not is_challenge
                attempt = {'strategy': strategy, 'status': status, 'challenge': is_challenge,
                           'success': success, 'body_sha256': hashlib.sha256(body.encode()).hexdigest()}
            except Exception as error:
                attempt = {'strategy': strategy, 'status': None, 'challenge': False,
                           'success': False, 'error_type': type(error).__name__}
            attempt['duration_seconds'] = time.perf_counter()-started
            attempts.append(attempt)
            if success:
                break
        return {'content': body if success else None, 'challenged': was_challenged,
                'recovered': was_challenged and success, 'success': success, 'attempts': attempts}


def recovery_metrics(results):
    results = list(results)
    challenges = [r for r in results if r['challenged']]
    recovered = sum(r['recovered'] is True for r in challenges)
    return {'requests': len(results), 'challenged_requests': len(challenges),
            'recovered_requests': recovered, 'attempts': sum(len(r['attempts']) for r in results),
            'bypass_fraction': recovered/len(challenges) if challenges else None}
