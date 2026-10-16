"""Durable UTC-day token reservations shared across gateway pilot batches.

Conservative bounds are supplied before dispatch. Missing/invalid usage never
releases a dispatched allocation for free. UTC rollover retains old reservations
and all history; their eventual settlements stay in the original request bucket.
"""
from datetime import datetime,timezone,date
import json
import re
import uuid
from faultseeker.core.spend_guard import SpendGuard,DispatchNotStarted

class DailyTokenLimitReached(DispatchNotStarted):
    pass

class DailyTokenGuard:
    def __init__(self,ledger_path,limit_tokens=7_000_000,now_utc=None):
        self._integer(limit_tokens)
        if not 0<limit_tokens<=7_000_000:raise ValueError('Daily token limit must be within 1..7000000')
        self.limit_tokens=limit_tokens
        self.now_utc=now_utc or (lambda:datetime.now(timezone.utc))
        self._storage=SpendGuard(ledger_path=ledger_path)
    @staticmethod
    def _integer(value):
        if type(value) is not int or value<0:raise ValueError('Token counts must be nonnegative integers')
        return value
    @staticmethod
    def _day(value):
        if not isinstance(value,str):raise ValueError('UTC day must be ISO date')
        try:parsed=date.fromisoformat(value)
        except ValueError:raise ValueError('UTC day must be ISO date') from None
        if parsed.isoformat()!=value:raise ValueError('UTC day must be ISO date')
        return value
    def _bucket(self):
        now=self.now_utc()
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Timezone-aware UTC clock required')
        return now.astimezone(timezone.utc).date().isoformat()
    def _read(self):
        path=self._storage.ledger_path
        if not path.exists():return {'schema':1,'time_zone':'UTC','buckets':{},'reservations':{},'events':[],'imports':{}}
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            if (data.get('schema')!=1 or data.get('time_zone')!='UTC'
                    or any(not isinstance(data.get(k),dict) for k in ('buckets','reservations','imports'))
                    or not isinstance(data.get('events'),list)):raise ValueError('Invalid token ledger')
            for day,bucket in data['buckets'].items():
                self._day(day);self._integer(bucket['used'])
            for record in data['reservations'].values():
                self._day(record['bucket']);self._integer(record['reserved'])
                if record['bucket'] not in data['buckets']:raise ValueError('Unknown reservation bucket')
            return data
        except (KeyError,TypeError,AttributeError,json.JSONDecodeError):
            raise ValueError('Invalid token ledger; refusing reset') from None
    def _write(self,state):self._storage._write(state)
    @staticmethod
    def _ensure(state,bucket):return state['buckets'].setdefault(bucket,{'used':0})
    def reserve(self,input_bound,max_output):
        total=self._integer(input_bound)+self._integer(max_output)
        if total<=0:raise ValueError('Positive token reservation required')
        day=self._bucket()
        with self._storage._locked():
            state=self._read();bucket=self._ensure(state,day)
            pending=sum(r['reserved'] for r in state['reservations'].values() if r['bucket']==day)
            if bucket['used']+pending+total>self.limit_tokens:
                raise DailyTokenLimitReached('Daily UTC token budget exhausted before dispatch')
            reservation=uuid.uuid4().hex
            state['reservations'][reservation]={'bucket':day,'reserved':total,'input_bound':input_bound,'max_output':max_output}
            state['events'].append({'event':'reserve','id':reservation,'bucket':day,'tokens':total})
            self._write(state);return reservation
    def settle(self,reservation,prompt_tokens=None,completion_tokens=None,failed=False):
        malformed=False
        if prompt_tokens is None and completion_tokens is None:measured=None
        else:
            try:measured=self._integer(prompt_tokens)+self._integer(completion_tokens)
            except ValueError:measured=None;malformed=True
        with self._storage._locked():
            state=self._read()
            if reservation not in state['reservations']:raise ValueError('Unknown or already settled token reservation')
            record=state['reservations'].pop(reservation);day=record['bucket']
            charge=record['reserved'] if measured is None else measured
            self._ensure(state,day)['used']+=charge
            state['events'].append({'event':'settle','id':reservation,'bucket':day,'tokens':charge,
                'failed':bool(failed),'usage_source':'provider' if measured is not None else 'reservation',
                'usage_invalid':malformed,'prompt_tokens':prompt_tokens if measured is not None else None,
                'completion_tokens':completion_tokens if measured is not None else None})
            self._write(state)
        if malformed:raise ValueError('Invalid provider token usage; full reservation charged')
        return charge
    def _import_once(self,source_id,day,tokens,evidence,usage_source,details):
        self._day(day);self._integer(tokens)
        if (not isinstance(source_id,str) or not source_id.strip() or not isinstance(evidence,dict)
                or not isinstance(evidence.get('path'),str) or not evidence['path']
                or not re.fullmatch('[0-9a-f]{64}',str(evidence.get('sha256','')))):
            raise ValueError('Historical import requires source ID and SHA-bound evidence')
        record={'bucket':day,'tokens':tokens,'evidence':dict(evidence),'usage_source':usage_source,**details}
        with self._storage._locked():
            state=self._read()
            if source_id in state['imports']:
                if state['imports'][source_id]!=record:raise ValueError('Conflicting historical token import')
                return 0
            state['imports'][source_id]=record;self._ensure(state,day)['used']+=tokens
            state['events'].append({'event':'historical-import','source_id':source_id,**record})
            self._write(state);return tokens
    def import_usage_once(self,source_id,day,prompt_tokens,completion_tokens,evidence_binding):
        return self._import_once(source_id,day,self._integer(prompt_tokens)+self._integer(completion_tokens),
            evidence_binding,'provider',{'prompt_tokens':prompt_tokens,'completion_tokens':completion_tokens})
    def import_allocation_once(self,source_id,day,conservative_tokens,evidence_binding):
        """Explicit historical missing-usage allocation; never infer zero usage."""
        return self._import_once(source_id,day,conservative_tokens,evidence_binding,'conservative-allocation',{})
    def report(self):
        day=self._bucket()
        with self._storage._locked():
            state=self._read();buckets={}
            for key,value in state['buckets'].items():
                reserved=sum(r['reserved'] for r in state['reservations'].values() if r['bucket']==key)
                buckets[key]={'used':value['used'],'reserved':reserved,'remaining':max(0,self.limit_tokens-value['used']-reserved)}
            current=buckets.get(day,{'used':0,'reserved':0,'remaining':self.limit_tokens})
            return {'bucket':day,'time_zone':'UTC','limit_tokens':self.limit_tokens,**current,
                    'buckets':buckets,'reservations':state['reservations'],'events':state['events'],'imports':state['imports']}
