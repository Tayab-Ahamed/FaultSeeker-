import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import Mock,patch
from urllib.error import URLError
import ssl
import pytest

from benchmark import nara_http_transport as m

def test_nested_urlerror_ssl_reason_class_not_message():
 e=URLError(ssl.SSLError(1,'fixture-secret https://private.invalid'))
 assert m._safe_error_details(e,'open')=={'worker_error_type':'URLError','phase':'open','reason_type':'SSLError','errno':1}

def test_numeric_oserror_only():
 d=m._safe_error_details(OSError(13,'fixture-secret'),'read')
 assert d=={'worker_error_type':'PermissionError','phase':'read','errno':13}

def test_unknown_class_names_and_phase_are_not_retained():
 Evil=type('Bearer_fixture-secret',(Exception,),{})
 assert m._safe_error_details(Evil('secret'),'https://private.invalid')=={'worker_error_type':'UnknownError','phase':'unknown'}

def test_exception_diagnostic_filters_untrusted_payload():
 d=m.TransportWorkerError({'worker_error_type':'https://secret','phase':'read','errno':True,'http_status':700,'url':'secret','body':'secret','reason_type':'Bearer_secret'})
 assert d.diagnostic=={'worker_error_type':'UnknownError','phase':'read'}
 assert 'secret' not in str(d)

def test_typed_parent_worker_packet_failure_not_swallowed():
 child=Mock();child.returncode=0;child.communicate.return_value=(b'{"ok":false,"diagnostic":{"worker_error_type":"URLError","phase":"open","reason_type":"SSLError","errno":1,"body":"fixture-secret"}}',None)
 with patch.object(m.subprocess,'Popen',return_value=child):
  with pytest.raises(m.TransportWorkerError) as caught:m.http_transport(m.ENDPOINT,{'Authorization':'Bearer fixture-secret'},b'{}',3)
 assert caught.value.diagnostic=={'worker_error_type':'URLError','phase':'open','reason_type':'SSLError','errno':1}
 assert 'fixture-secret' not in str(caught.value)

@pytest.mark.parametrize('packet',[b'not-json',b'[]',b'{"ok":false,"diagnostic":"fixture-secret"}'])
def test_corrupt_packet_has_only_safe_diagnostics(packet):
 child=Mock();child.returncode=0;child.communicate.return_value=(packet,None)
 with patch.object(m.subprocess,'Popen',return_value=child):
  with pytest.raises(m.TransportWorkerError) as caught:m.http_transport(m.ENDPOINT,{},b'{}',3)
 assert 'fixture-secret' not in str(caught.value)
 assert set(caught.value.diagnostic)<= {'worker_error_type','phase','reason_type','errno','winerror','ssl_verify_code','http_status'}


def test_ssl_verification_numeric_code_retained_without_text():
 exc=ssl.SSLCertVerificationError(1,'fixture-secret');exc.verify_code=62;exc.verify_message='fixture-secret'
 d=m._safe_error_details(URLError(exc),'open')
 assert d=={'worker_error_type':'URLError','phase':'open','reason_type':'SSLCertVerificationError','errno':1,'ssl_verify_code':62}
 assert 'fixture-secret' not in repr(d)

def test_safe_observed_http_status_survives_payload_filtering():
 d=m.TransportWorkerError({'worker_error_type':'ConnectionResetError','phase':'read','http_status':429,'winerror':10054,'body':'fixture-secret'})
 assert d.diagnostic=={'worker_error_type':'ConnectionResetError','phase':'read','http_status':429,'winerror':10054}
