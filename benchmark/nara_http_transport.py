"""Isolated HTTP transport with a parent-enforced total request deadline.

The deadline includes process startup and IPC. On expiry the parent kills,
drains and reaps the worker before raising. Cleanup/OS scheduling adds a small
unbounded-by-Python tolerance; this cannot cancel an accepted remote inference.
Worker output contains response bytes only after credential-echo checks.
"""
import base64
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

ENDPOINT='https://router.bynara.id/v1/chat/completions'


_ERROR_TYPES=frozenset(('URLError','HTTPError','SSLError','SSLCertVerificationError','TimeoutError',
    'ConnectionError','ConnectionResetError','ConnectionAbortedError','ConnectionRefusedError',
    'BrokenPipeError','OSError','PermissionError','FileNotFoundError','gaierror','herror',
    'ValueError','TypeError','KeyError','JSONDecodeError','UnicodeDecodeError','Error','UnknownError'))
_PHASES=frozenset(('spawn','request','open','read','response','decode','worker','unknown'))

def _sanitize_diagnostic(value):
    value=value if isinstance(value,dict) else {}
    name=value.get('worker_error_type');phase=value.get('phase')
    out={'worker_error_type':name if isinstance(name,str) and name in _ERROR_TYPES else 'UnknownError',
         'phase':phase if isinstance(phase,str) and phase in _PHASES else 'unknown'}
    reason=value.get('reason_type')
    if isinstance(reason,str) and reason in _ERROR_TYPES:out['reason_type']=reason
    for key in ('errno','winerror','ssl_verify_code'):
        number=value.get(key)
        if type(number) is int and -(2**31)<=number<2**31:out[key]=number
    status=value.get('http_status')
    if type(status) is int and 100<=status<=599:out['http_status']=status
    return out

class TransportWorkerError(ValueError):
    def __init__(self,diagnostic):
        self.diagnostic=_sanitize_diagnostic(diagnostic)
        super().__init__('HTTP transport worker failed safely')

def _safe_error_details(exc,phase):
    from urllib.error import URLError
    data={'worker_error_type':type(exc).__name__,'phase':phase}
    cause=exc
    if isinstance(exc,URLError) and isinstance(exc.reason,BaseException):
        cause=exc.reason;data['reason_type']=type(cause).__name__
    for key,attribute in (('errno','errno'),('winerror','winerror'),('ssl_verify_code','verify_code')):
        number=getattr(cause,attribute,None)
        if type(number) is int:data[key]=number
    return _sanitize_diagnostic(data)

class TransportDeadlineExceeded(TimeoutError):
    pass

def _validate_timeout(timeout):
    if type(timeout) not in (int,float) or not 0<timeout or not math.isfinite(timeout):
        raise ValueError('Transport deadline must be finite and positive')

def _validate_url(url,loopback=False):
    if not loopback:
        if url!=ENDPOINT:raise ValueError('Unexpected gateway endpoint')
        return
    try:
        parsed=urlsplit(url)
        valid=(parsed.scheme=='http' and parsed.hostname=='127.0.0.1' and parsed.port is not None
               and not parsed.username and not parsed.password and not parsed.fragment)
    except (ValueError,TypeError):valid=False
    if not valid:raise ValueError('Private transport test seam requires explicit IPv4 loopback')

def _transport(url,headers,body,timeout,*,loopback=False):
    _validate_url(url,loopback);_validate_timeout(timeout)
    if not isinstance(body,bytes) or not isinstance(headers,dict):raise ValueError('Transport requires bytes and header dictionary')
    started=time.monotonic()
    payload=json.dumps({'url':url,'headers':headers,'body':base64.b64encode(body).decode('ascii'),'timeout':timeout}).encode('utf-8')
    args=[sys.executable,'-I','-S',str(Path(__file__).resolve()),'--loopback-worker' if loopback else '--worker']
    options={'stdin':subprocess.PIPE,'stdout':subprocess.PIPE,'stderr':subprocess.DEVNULL}
    if os.name=='nt':options['creationflags']=subprocess.CREATE_NO_WINDOW
    try:child=subprocess.Popen(args,**options)
    except Exception as exc:raise TransportWorkerError(_safe_error_details(exc,'spawn')) from None
    finished=threading.Event();expired=threading.Event();watchdog=None
    try:
        remaining=timeout-(time.monotonic()-started)
        if remaining<=0:raise subprocess.TimeoutExpired(args,timeout)
        # Windows communicate() writes stdin synchronously. Its own timeout
        # cannot interrupt a full pipe, so a joined watchdog kills the worker
        # even if the calling thread is blocked sending the request payload.
        def expire():
            if not finished.wait(remaining):
                expired.set()
                try:child.kill()
                except ProcessLookupError:pass
        watchdog=threading.Thread(target=expire,name='nara-http-deadline')
        watchdog.start()
        stdout,_=child.communicate(payload,timeout=remaining)
    except subprocess.TimeoutExpired:
        child.kill();child.communicate();child.wait()
        raise TransportDeadlineExceeded('HTTP transport total deadline exceeded; worker reaped') from None
    except BaseException:
        if child.poll() is None:child.kill()
        child.communicate();child.wait()
        if expired.is_set():
            raise TransportDeadlineExceeded('HTTP transport total deadline exceeded; worker reaped') from None
        raise
    finally:
        finished.set()
        if watchdog is not None:watchdog.join()
    if expired.is_set() or time.monotonic()-started>=timeout:
        raise TransportDeadlineExceeded('HTTP transport total deadline exceeded; worker reaped')
    if child.returncode!=0:raise TransportWorkerError({'worker_error_type':'UnknownError','phase':'worker'})
    try:
        result=json.loads(stdout)
        if not isinstance(result,dict):raise ValueError('Invalid worker packet')
        if result.get('ok') is not True:raise TransportWorkerError(result.get('diagnostic'))
        response=base64.b64decode(result['body'],validate=True)
        returned=result['url'];status=result['status']
        _validate_url(returned,loopback)
        if returned!=url or type(status) is not int:raise ValueError('Invalid transport response identity')
    except TransportWorkerError:raise
    except Exception as exc:raise TransportWorkerError(_safe_error_details(exc,'decode')) from None
    if time.monotonic()-started>=timeout:
        raise TransportDeadlineExceeded('HTTP transport total deadline exceeded; worker reaped')
    return status,response,returned

def http_transport(url,headers,body,timeout):
    return _transport(url,headers,body,timeout)

def _loopback_transport(url,headers,body,timeout):
    """Private local-server integration seam; never a production endpoint override."""
    return _transport(url,headers,body,timeout,loopback=True)

def _worker(loopback=False):
    # Intentionally stdlib-only: isolated Python does not import project code,
    # dotenv, model SDKs, ledger machinery, or credentials from files.
    from urllib import request,error
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise ValueError('Redirect refused')
    phase='request';observed_status=None
    try:
        packet=json.loads(sys.stdin.buffer.read())
        url=packet['url'];_validate_url(url,loopback);_validate_timeout(packet['timeout'])
        headers=packet['headers'];body=base64.b64decode(packet['body'],validate=True)
        # No environment proxies on the loopback seam; production retains
        # default platform proxy configuration and TLS certificate validation.
        handlers=[NoRedirect()]
        if loopback:handlers.append(request.ProxyHandler({}))
        opener=request.build_opener(*handlers)
        req=request.Request(url,data=body,headers=headers,method='POST')
        phase='open'
        try:
            response=opener.open(req,timeout=packet['timeout'])
        except error.HTTPError as exc:response=exc
        observed_status=response.code
        phase='read'
        with response:
            raw=response.read();status=response.code;returned=response.geturl()
        phase='response'
        if returned!=url or 300<=status<400:raise ValueError('Redirect refused')
        authorization=next((v for k,v in headers.items() if k.lower()=='authorization'),'')
        secret=authorization[7:] if authorization.lower().startswith('bearer ') else authorization
        if secret:
            if secret.encode('utf-8') in raw:raise ValueError('Credential echo refused')
            try:decoded=json.loads(raw)
            except (ValueError,UnicodeDecodeError):decoded=None
            if decoded is not None and secret in json.dumps(decoded,ensure_ascii=False):
                raise ValueError('Credential echo refused')
        output={'ok':True,'status':status,'url':returned,'body':base64.b64encode(raw).decode('ascii')}
    except BaseException as exc:
        diagnostic=_safe_error_details(exc,phase)
        if type(observed_status) is int and 100<=observed_status<=599:diagnostic['http_status']=observed_status
        output={'ok':False,'diagnostic':diagnostic}
    sys.stdout.buffer.write(json.dumps(output).encode('utf-8'));sys.stdout.buffer.flush()

if __name__=='__main__':
    if sys.argv[1:]==['--worker']:_worker()
    elif sys.argv[1:]==['--loopback-worker']:_worker(loopback=True)
    else:raise SystemExit(2)
