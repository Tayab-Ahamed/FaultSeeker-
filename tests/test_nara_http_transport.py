import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import pytest
from benchmark.nara_http_transport import http_transport,ENDPOINT,TransportDeadlineExceeded,_loopback_transport

@pytest.mark.parametrize('timeout',[0,-1,float('nan'),float('inf'),True,'1',None])
def test_invalid_timeout_rejected(timeout):
 with pytest.raises(ValueError):http_transport(ENDPOINT,{},b'{}',timeout)

def test_production_rejects_url_before_spawn():
 with patch('benchmark.nara_http_transport.subprocess.Popen') as process:
  with pytest.raises(ValueError):http_transport('http://127.0.0.1:1',{},b'{}',1)
  process.assert_not_called()

@pytest.fixture
def server():
 state={'requests':0,'closed':threading.Event()}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   state['requests']+=1
   self.rfile.read(int(self.headers.get('Content-Length','0')))
   if self.path=='/trickleheaders':
    try:
     for byte in b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}':
      self.connection.sendall(bytes([byte]));time.sleep(.1)
    except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):state['closed'].set()
    return
   if self.path=='/headers':time.sleep(3)
   if self.path=='/redirect':
    self.send_response(302);self.send_header('Location','http://127.0.0.1:1/other');self.end_headers();return
   status=429 if self.path in ('/error','/shorterror') else 200
   payload=(b'fixture-secret' if self.path=='/echo' else b'{\"echo\":\"fixture-\\u0073ecret\"}' if self.path=='/escaped' else b'{}')
   try:
    self.send_response(status);self.send_header('Content-Length','100' if self.path in ('/trickle','/error') else str(len(payload)));self.end_headers()
   except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):state['closed'].set();return
   try:
    if self.path in ('/trickle','/error'):
     for _ in range(100):self.wfile.write(b'x');self.wfile.flush();time.sleep(.1)
    else:self.wfile.write(payload);self.wfile.flush()
   except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):state['closed'].set()
 srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);srv.daemon_threads=True
 thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
 yield 'http://127.0.0.1:'+str(srv.server_port),state
 srv.shutdown();srv.server_close();thread.join(2)

def test_real_worker_preserves_response(server):
 url,state=server
 assert _loopback_transport(url+'/ok',{},b'{}',3)==(200,b'{}',url+'/ok')
 assert state['requests']==1

@pytest.mark.parametrize('path',['/headers','/trickleheaders','/trickle','/error'])
def test_real_worker_total_deadline_kills_reaps_and_closes(server,path):
 url,state=server;children=[];real=subprocess.Popen
 def spawn(*args,**kwargs):
  child=real(*args,**kwargs);children.append(child);return child
 started=time.monotonic()
 with patch('benchmark.nara_http_transport.subprocess.Popen',side_effect=spawn):
  with pytest.raises(TransportDeadlineExceeded) as caught:_loopback_transport(url+path,{'Authorization':'Bearer fixture-secret'},b'{}',1.5)
 assert time.monotonic()-started<3.5
 assert len(children)==1 and children[0].poll() is not None
 assert 'fixture-secret' not in str(caught.value)
 if path!='/headers':assert state['closed'].wait(2)
 assert state['requests']==1

def test_redirect_rejected_without_secret_error(server):
 url,state=server
 with pytest.raises(ValueError) as caught:_loopback_transport(url+'/redirect',{'Authorization':'Bearer fixture-secret'},b'{}',3)
 assert 'fixture-secret' not in str(caught.value)
 assert state['requests']==1

def test_private_seam_rejects_nonloopback():
 with pytest.raises(ValueError):_loopback_transport('http://example.com/x',{},b'{}',1)


def test_http_error_response_is_preserved(server):
 url,state=server
 assert _loopback_transport(url+'/shorterror',{},b'{}',3)==(429,b'{}',url+'/shorterror')

def test_spawn_error_is_sanitized():
 with patch('benchmark.nara_http_transport.subprocess.Popen',side_effect=OSError('fixture-secret')):
  with pytest.raises(ValueError) as caught:http_transport(ENDPOINT,{'Authorization':'Bearer fixture-secret'},b'{}',1)
 assert 'fixture-secret' not in str(caught.value)


def test_deadline_includes_spawn_and_reaps_before_return():
 child=__import__('unittest.mock',fromlist=['Mock']).Mock();child.poll.return_value=1
 with patch('benchmark.nara_http_transport.subprocess.Popen',return_value=child) as spawn,patch('benchmark.nara_http_transport.time.monotonic',side_effect=[0,2]):
  with pytest.raises(TransportDeadlineExceeded):http_transport(ENDPOINT,{'Authorization':'Bearer fixture-secret'},b'{}',1)
 child.kill.assert_called_once();child.communicate.assert_called_once_with();child.wait.assert_called_once()
 assert 'fixture-secret' not in repr(spawn.call_args.args)
 assert spawn.call_args.kwargs['stderr']==subprocess.DEVNULL


@pytest.mark.parametrize('path',['/echo','/escaped'])
def test_worker_blocks_raw_or_json_escaped_credential_echo(server,path):
 url,state=server
 with pytest.raises(ValueError) as caught:_loopback_transport(url+path,{'Authorization':'Bearer fixture-secret'},b'{}',3)
 assert 'fixture-secret' not in str(caught.value)
 assert state['requests']==1

def test_worker_crash_is_sanitized():
 child=__import__('unittest.mock',fromlist=['Mock']).Mock();child.returncode=1;child.communicate.return_value=(b'',None)
 with patch('benchmark.nara_http_transport.subprocess.Popen',return_value=child):
  with pytest.raises(ValueError) as caught:http_transport(ENDPOINT,{'Authorization':'Bearer fixture-secret'},b'{}',3)
 assert 'fixture-secret' not in str(caught.value)


def test_deadline_also_interrupts_blocked_stdin_write():
 """Windows communicate() writes stdin synchronously before its timeout wait."""
 import sys
 children=[];errors=[];real=subprocess.Popen
 def spawn(args,**kwargs):
  child=real([sys.executable,'-I','-S','-c','import time; time.sleep(30)'],**kwargs)
  children.append(child);return child
 def invoke():
  try:http_transport(ENDPOINT,{},b'x'*1000000,1.5)
  except BaseException as exc:errors.append(exc)
 thread=threading.Thread(target=invoke)
 try:
  with patch('benchmark.nara_http_transport.subprocess.Popen',side_effect=spawn):
   thread.start();thread.join(3)
   completed_by_deadline=not thread.is_alive()
   # Failure cleanup must not leave the pre-fix blocked writer or worker alive.
   if not completed_by_deadline:
    for child in children:
     if child.poll() is None:child.kill()
    thread.join(3)
  assert not thread.is_alive()
  assert completed_by_deadline,'Parent blocked writing stdin past total deadline'
  assert len(errors)==1 and isinstance(errors[0],TransportDeadlineExceeded)
  assert len(children)==1 and children[0].poll() is not None
 finally:
  for child in children:
   if child.poll() is None:child.kill()
   child.wait()
  if thread.is_alive():thread.join(3)
