import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmark.nara_pilot_provider import NaraPilot, StudyStop, MODEL, ENDPOINT
from faultseeker.core.llm_router import HybridLLMRouter

class Guard:
 def __init__(self):self.events=[]
 def reserve(self,*args):self.events.append('reserve');return 'r'
 def settle(self,*args,**kwargs):self.events.append('settle');return 0.001

class NaraPilotTests(unittest.TestCase):
 def setUp(self):
  self.pricing=patch.dict('faultseeker.core.llm_router.COST_RATES',{MODEL:{'input':0.1,'output':0.2}});self.pricing.start();self.addCleanup(self.pricing.stop)
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.guard=Guard();self.bodies=[];self.now=[0.0]
  self.router=HybridLLMRouter(cloud_model=MODEL,routing_strategy='cloud-only',remote_model_ids=[MODEL],spend_guard=self.guard)
 def response(self,model=MODEL):
  return json.dumps({'model':model,'choices':[{'message':{'content':'{"ok":true}'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}).encode()
 def transport(self,url,headers,body,timeout):
  self.assertEqual(self.guard.events[-1],'reserve');self.bodies.append(json.loads(body));return 200,self.response(),url
 def pilot(self,transport=None,max_calls=20):
  return NaraPilot(api_key='secret-credential',router=self.router,output_dir=self.tmp.name,transport=transport or self.transport,clock=lambda:self.now[0],sleep=lambda n:self.now.__setitem__(0,self.now[0]+n),max_calls=max_calls)
 def test_full_prompt_reserved_and_usage(self):
  p=self.pilot();a=p.factory('sys','reasoning_agent');self.assertTrue(a.query('x'*15000)['ok']);self.assertEqual(len(self.bodies[0]['messages'][-1]['content']),15000);self.assertEqual(self.guard.events,['reserve','settle']);self.assertEqual(a.providers[MODEL].last_usage['prompt_tokens'],10)
 def test_cap_before_reservation(self):
  p=self.pilot(max_calls=1);a=p.factory('sys');a.query('one')
  with self.assertRaises(StudyStop):a.query('two')
  self.assertEqual(self.guard.events,['reserve','settle'])
 def test_starts_spaced_across_roles(self):
  p=self.pilot();p.factory('s').query('one');p.factory('s','processing_agent').query('two');self.assertEqual(self.now[0],5)
 def test_auth_failure_settles_then_stops(self):
  p=self.pilot(transport=lambda *args:(401,b'{"error":"auth"}',ENDPOINT));a=p.factory('s')
  with self.assertRaises(ValueError):a.query('one')
  with self.assertRaises(StudyStop):a.query('two')
  self.assertEqual(self.guard.events,['reserve','settle'])
 def test_credential_echo_never_persisted(self):
  p=self.pilot(transport=lambda *args:(200,b'{"echo":"secret-credential"}',ENDPOINT));a=p.factory('s')
  with self.assertRaises(ValueError):a.query('one')
  self.assertNotIn('secret-credential',''.join(x.read_text(encoding='utf-8') for x in Path(self.tmp.name).glob('*.json')))
 def test_history_is_exactly_last_two_completed_turns(self):
  p=self.pilot();a=p.factory('system')
  for word in ['one','two','three','four']:a.query(word)
  msgs=self.bodies[-1]['messages'];self.assertEqual(len(msgs),6);self.assertEqual([x['content'] for x in msgs if x['role']=='user'],['two','three','four'])
 def test_endpoint_mismatch_stops_without_retry(self):
  p=self.pilot(transport=lambda *args:(200,self.response(),'https://other.example/v1/chat/completions'));a=p.factory('s')
  with self.assertRaises(ValueError):a.query('one')
  with self.assertRaises(StudyStop):a.query('two')
  self.assertEqual(p.calls,1)
 def test_artifact_hash_matches_exact_request(self):
  import hashlib
  p=self.pilot();a=p.factory('s');a.query('hello')
  record=json.loads((Path(self.tmp.name)/'call-001.json').read_text(encoding='utf-8'))
  self.assertEqual(record['request_sha256'],hashlib.sha256(json.dumps(self.bodies[0],ensure_ascii=False).encode('utf-8')).hexdigest())
  self.assertEqual(record['usage']['total_tokens'],15);self.assertEqual(record['finish_reason'],'stop')
  self.assertNotIn('Authorization',json.dumps(record))
 def test_prompt_credential_stops_before_transport(self):
  p=self.pilot();a=p.factory('s')
  with self.assertRaises(ValueError):a.query('secret-credential')
  self.assertEqual(p.calls,0);self.assertEqual(self.guard.events,['reserve','settle'])
  with self.assertRaises(StudyStop):a.query('safe')
 def test_wrong_alias_stops(self):
  p=self.pilot(transport=lambda *args:(200,self.response('other'),ENDPOINT));a=p.factory('s')
  with self.assertRaises(ValueError):a.query('one')
  with self.assertRaises(StudyStop):a.query('two')

if __name__=='__main__':unittest.main()
