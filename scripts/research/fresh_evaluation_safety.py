"""Offline-testable safeguards for a future collector; no transport or dataset I/O."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time

METHODS=frozenset(('eth_chainId','eth_getTransactionByHash','eth_getTransactionReceipt','debug_traceTransaction'))
EVENTS=frozenset(('request_started','request_finished','transport_error','stop_billing','rate_limited','rate_limit_exhausted'))
BILLING=re.compile(r'\b(?:upgrade|paid(?:\s+plan)?|billing|payment|credit\s*card|add\s+(?:a\s+)?card|free[\s_-]*(?:tier[\s_-]*)?quota|quota.{0,30}(?:exhausted|exceeded)|(?:exhausted|exceeded).{0,30}quota)\b',re.I)
BACKOFF=(2.,4.,8.)

class SafetyStop(RuntimeError):
    pass

def billing_stop(status,body):
    if status==402:return True
    if isinstance(body,str):return bool(BILLING.search(body))
    if isinstance(body,dict):return any(billing_stop(None,v) for v in body.values())
    if isinstance(body,(list,tuple)):return any(billing_stop(None,v) for v in body)
    return False

def rate_limited(status,body):
    if status==429:return True
    error=body.get('error') if isinstance(body,dict) else None
    return isinstance(error,dict) and (error.get('code') in (429,-32005,-32016) or 'rate limit' in str(error.get('message','')).lower())

class RequestLedger:
    """Append-only allowlisted metadata. Never accepts payloads, URLs or keys."""
    def __init__(self,path):self.path=Path(path);self._lock=threading.Lock()
    def append(self,*,event,method,row_index,attempt,http_status=None):
        if event not in EVENTS or method not in METHODS:raise ValueError('Unsupported ledger enum')
        if type(row_index) is not int or row_index<0 or type(attempt) is not int or not 0<=attempt<=3:raise ValueError('Invalid ledger index')
        if http_status is not None and (type(http_status) is not int or not 100<=http_status<=599):raise ValueError('Invalid HTTP status')
        record=dict(event=event,method=method,row_index=row_index,attempt=attempt,http_status=http_status)
        data=(json.dumps(record,sort_keys=True)+'\n').encode()
        with self._lock:
            fd=os.open(self.path,os.O_APPEND|os.O_CREAT|os.O_WRONLY,0o600)
            try:
                with os.fdopen(fd,'ab') as handle:handle.write(data);handle.flush();os.fsync(handle.fileno())
            except BaseException:
                raise

class RequestGate:
    """Serialize callback requests with >=1 second starts and bounded retries."""
    def __init__(self,ledger,*,clock=time.monotonic,sleep=time.sleep):
        self.ledger=ledger;self.clock=clock;self.sleep=sleep;self.last_start=None;self.stopped=False;self._lock=threading.Lock()
    def call(self,transport,*,method,row_index):
        # Transport is supplied by the caller; this module never opens a socket.
        with self._lock:
            if self.stopped:raise SafetyStop('Request gate already stopped')
            for attempt in range(4):
                if self.last_start is not None:
                    while self.clock()-self.last_start<1.:
                        self.sleep(1.-(self.clock()-self.last_start))
                self.ledger.append(event='request_started',method=method,row_index=row_index,attempt=attempt)
                self.last_start=self.clock()
                try:status,body=transport()
                except Exception:
                    self.stopped=True
                    self.ledger.append(event='transport_error',method=method,row_index=row_index,attempt=attempt)
                    raise SafetyStop('Transport failed; details omitted') from None
                if billing_stop(status,body):
                    self.stopped=True
                    self.ledger.append(event='stop_billing',method=method,row_index=row_index,attempt=attempt,http_status=status)
                    raise SafetyStop('Billing or free-quota stop')
                if not rate_limited(status,body):
                    self.ledger.append(event='request_finished',method=method,row_index=row_index,attempt=attempt,http_status=status)
                    return status,body
                self.ledger.append(event='rate_limited',method=method,row_index=row_index,attempt=attempt,http_status=status)
                if attempt==3:
                    self.stopped=True
                    self.ledger.append(event='rate_limit_exhausted',method=method,row_index=row_index,attempt=attempt,http_status=status)
                    raise SafetyStop('Rate-limit retries exhausted')
                self.sleep(BACKOFF[attempt])

def verify_frozen_inputs(expected):
    """Compare caller-pinned SHA256 values; never rewrite a frozen artifact."""
    if not expected:raise ValueError('No frozen inputs supplied')
    for path,digest in expected.items():
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Invalid pinned digest')
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise SafetyStop('Frozen input hash mismatch')

def acquire_score_lock(path,expected):
    """Verify inputs and atomically claim a permanent one-score marker.

    Marker is deliberately retained after failure or success. No automatic retry
    can score the same frozen run twice. Caller owns any explicit recovery.
    """
    verify_frozen_inputs(expected)
    try:
        with Path(path).open('x',encoding='utf-8') as handle:
            handle.write('score_claimed\n');handle.flush();os.fsync(handle.fileno())
    except FileExistsError:
        raise SafetyStop('Scoring already claimed') from None
    verify_frozen_inputs(expected)
