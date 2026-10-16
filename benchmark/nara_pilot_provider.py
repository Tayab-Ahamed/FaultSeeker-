"""Bounded real NaraRouter cloud transport; no local or vendor-identity claim."""
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from benchmark.nara_http_transport import http_transport, TransportDeadlineExceeded, ENDPOINT
from faultseeker.core.llm_router import RoutedAgent
from faultseeker.utils.agent import AbstractAgent

MODEL='agnes-2.5-flash'

class StudyStop(BaseException):
    """Study boundary must escape broad pipeline Exception handlers."""

class NaraPilot:
    def __init__(self, *, api_key, router, output_dir, transport=http_transport,
                 clock=time.monotonic, sleep=time.sleep,max_calls=20,daily_token_guard=None,transport_timeout=60):
        if not isinstance(api_key,str) or not api_key.strip():raise ValueError('BYNARA_API_KEY unavailable')
        if max_calls is None:
            if daily_token_guard is None:raise ValueError('Uncapped pilot requires a daily token guard')
        elif type(max_calls) is not int or not 1<=max_calls<=20:raise ValueError('Pilot call cap must be between 1 and 20')
        if type(transport_timeout) not in (int,float) or not math.isfinite(transport_timeout) or not 0<transport_timeout<=600:
            raise ValueError('Transport deadline must be within 0..600 seconds')
        if (router.cloud_model!=MODEL or router.routing_strategy!='cloud-only'
                or router._is_local_model(MODEL) or router.spend_guard is None):
            raise ValueError('Pilot requires explicit cloud identity and shared priced spend guard')
        self._key=api_key;self.router=router;self.output_dir=Path(output_dir)
        self.transport=transport;self.clock=clock;self.sleep=sleep;self.max_calls=max_calls
        self.daily_token_guard=daily_token_guard
        self.transport_timeout=transport_timeout
        self.calls=0;self.last_start=None;self.stop_reason='';self.lock=threading.RLock()
    def _precheck(self):
        if self.stop_reason:raise StudyStop(self.stop_reason)
        if self.max_calls is not None and self.calls>=self.max_calls:raise StudyStop('Pilot request cap reached')
    def stop_after_analysis_error(self,error):
        """Domain errors are terminal too; never dispatch a recovery request.

        Persist only the error class, never its possibly sensitive message.
        StudyStop escapes the analyzer's ordinary Exception recovery loops.
        """
        with self.lock:
            if not self.stop_reason:
                self.stop_reason='Pilot stopped after analysis error: '+type(error).__name__
            raise StudyStop(self.stop_reason) from None
    def factory(self, task, role='', *, model_name=MODEL, router=None, agent_role=None):
        agent_role=role if agent_role is None else agent_role
        if model_name!=MODEL or (router is not None and router is not self.router):
            raise ValueError('Pilot cannot change model or shared router')
        def provider(system,model):
            if model!=MODEL:raise ValueError('Pilot model mismatch')
            return _Provider(self,system,agent_role)
        return _BoundAgent(self,RoutedAgent(task,self.router,agent_role,provider))
    def _record(self,record):
        # This scan precedes all filesystem writes, including exceptional bodies.
        encoded=json.dumps(record,ensure_ascii=False,sort_keys=True).encode('utf-8')
        if self._key.encode('utf-8') in encoded:
            self.stop_reason='Credential echo detected; unsafe artifact withheld'
            record={'call_number':self.calls,'status':'credential_echo_blocked',
                    'endpoint':ENDPOINT,'model':MODEL,'role':record.get('role',''),
                    'response_persisted':False,'request_persisted':False}
            encoded=json.dumps(record,sort_keys=True).encode('utf-8')
        self.output_dir.mkdir(parents=True,exist_ok=True)
        path=self.output_dir/('call-%03d.json'%self.calls)
        # Exclusive artifact creation refuses accidental experiment reuse.
        with path.open('x',encoding='utf-8') as handle:handle.write(encoded.decode('utf-8')+'\n')

class _BoundAgent:
    def __init__(self,pilot,agent):self.pilot=pilot;self.agent=agent
    def __getattr__(self,name):return getattr(self.agent,name)
    def reset_memory(self):return self.agent.reset_memory()
    def query(self,user_message,temperature=0,format='json'):
        # Lock spans reservation+dispatch+settlement; shared roles cannot overshoot.
        with self.pilot.lock:
            self.pilot._precheck()
            guard=self.pilot.router.spend_guard
            before=guard.report() if hasattr(guard, 'report') else None
            call_before=self.pilot.calls
            try:
                return self.agent.query(user_message,temperature,format)
            except Exception as exc:
                if not self.pilot.stop_reason:
                    self.pilot.stop_reason='Pilot stopped after '+type(exc).__name__
                raise
            finally:
                if before is not None and self.pilot.calls>call_before:
                    events=guard.report()['events'][len(before['events']):]
                    events=[e for e in events if e.get('model')==MODEL]
                    receipt={'call_number':self.pilot.calls,'model':MODEL,'ledger_events':events}
                    directory=self.pilot.output_dir/'ledger';directory.mkdir(parents=True,exist_ok=True)
                    path=directory/('call-%03d.json'%self.pilot.calls)
                    with path.open('x',encoding='utf-8') as handle:
                        json.dump(receipt,handle,indent=2);handle.write('\n')

class _Provider(AbstractAgent):
    def __init__(self,pilot,system,role):
        super().__init__(system, MODEL)
        self.pilot=pilot;self.role=role
    def _send_message(self,prompt,temperature=0):
        p=self.pilot;p._precheck()
        # Keep system + two completed turns + this full prompt, without slicing.
        messages=[self.memory[0]]+self.memory[1:][-4:]+[{'role':'user','content':prompt}]
        payload={'model':MODEL,'messages':messages,'temperature':temperature,'max_tokens':4096,'stream':False}
        body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        if p._key.encode('utf-8') in body:
            p.stop_reason='Credential echo detected in request';raise ValueError(p.stop_reason)
        if p.last_start is not None:
            wait=5-(p.clock()-p.last_start)
            if wait>0:p.sleep(wait)
        daily_reservation=None
        if p.daily_token_guard is not None:
            daily_reservation=p.daily_token_guard.reserve(2*len(body)+1024,4096)
        p.last_start=p.clock();p.calls+=1;self.last_usage=None
        record={'call_number':p.calls,'role':self.role,'endpoint':ENDPOINT,'requested_alias':MODEL,
                'request':payload,'request_sha256':hashlib.sha256(body).hexdigest(),
                'request_bytes':len(body),'timeout_seconds':p.transport_timeout,'history_policy':'system_plus_last_two_completed_turns',
                'timeout_scope':('total_transport_deadline' if p.transport is http_transport else 'injected_transport'),
                'billing_confirmed':False,'status':'dispatch_started'}
        try:
            status,raw,url=p.transport(ENDPOINT,{'Authorization':'Bearer '+p._key,'Content-Type':'application/json'},body,p.transport_timeout)
            record.update(http_status=status,response_sha256=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw),duration_seconds=p.clock()-p.last_start)
            if p._key.encode('utf-8') in raw:
                p.stop_reason='Credential echo detected in response';raise ValueError(p.stop_reason)
            record['response_text']=raw.decode('utf-8',errors='replace')
            if url!=ENDPOINT:
                p.stop_reason='Gateway endpoint mismatch';raise ValueError(p.stop_reason)
            if status in (401,403,402,429):p.stop_reason='Gateway HTTP '+str(status)+'; study stopped'
            if status!=200:raise ValueError('Gateway HTTP '+str(status))
            data=json.loads(raw.decode('utf-8'))
            if p._key in json.dumps(data,ensure_ascii=False):
                p.stop_reason='Credential echo detected in decoded response';raise ValueError(p.stop_reason)
            record['response']=data
            usage=data.get('usage') or {};self.last_usage=usage
            record['usage']=usage;record['returned_alias']=data.get('model')
            if data.get('model')!=MODEL:
                p.stop_reason='Gateway returned unexpected model alias';raise ValueError(p.stop_reason)
            choice=data['choices'][0];record['finish_reason']=choice.get('finish_reason')
            content=choice['message'].get('content') or ''
            if not content.strip():raise ValueError('Gateway returned empty visible content')
            if choice.get('finish_reason')=='length':raise ValueError('Gateway completion reached output cap')
            self.memory.extend([{'role':'user','content':prompt},{'role':'assistant','content':content}])
            record['status']='response_received'
            return content
        except Exception as exc:
            record['status']='failed';record['error_type']=type(exc).__name__
            record.setdefault('duration_seconds',p.clock()-p.last_start)
            if isinstance(exc,TransportDeadlineExceeded):record['transport_deadline_exceeded']=True
            # Never persist arbitrary exception strings: they may contain headers.
            raise ValueError('Nara pilot transport failed: '+type(exc).__name__) from None
        finally:
            try:
                if daily_reservation is not None:
                    usage=self.last_usage or {}
                    try:
                        charged=p.daily_token_guard.settle(daily_reservation,
                            usage.get('prompt_tokens'),usage.get('completion_tokens'),
                            failed=record['status']!='response_received')
                        state=p.daily_token_guard.report()
                        record['daily_token_accounting']={'reservation_id':daily_reservation,'charged_tokens':charged,
                            'state':{k:state[k] for k in ('bucket','time_zone','limit_tokens','used','reserved','remaining')}}
                    except Exception as exc:
                        record['status']='failed';record['daily_token_accounting_error']=type(exc).__name__
                        record['daily_token_reservation_id']=daily_reservation
                        raise ValueError('Daily token accounting failed safely') from None
            finally:p._record(record)
