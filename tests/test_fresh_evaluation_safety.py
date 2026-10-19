import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.research.fresh_evaluation_safety import RequestLedger,RequestGate,SafetyStop,billing_stop,verify_frozen_inputs,acquire_score_lock

class FakeTime:
    def __init__(self):self.now=0.;self.delays=[]
    def clock(self):return self.now
    def sleep(self,n):self.delays.append(n);self.now+=n

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'ledger.jsonl';self.ledger=RequestLedger(self.path);self.time=FakeTime();self.gate=RequestGate(self.ledger,clock=self.time.clock,sleep=self.time.sleep)
    def tearDown(self):self.tmp.cleanup()
    def call(self,transport):return self.gate.call(transport,method='eth_chainId',row_index=0)
    def test_throttle_and_append(self):
        starts=[]
        def transport():starts.append(self.time.now);return 200,{'result':'0x1'}
        self.call(transport);prefix=self.path.read_bytes();self.call(transport)
        self.assertEqual(starts,[0.,1.]);self.assertTrue(self.path.read_bytes().startswith(prefix));self.assertEqual(len(self.path.read_text().splitlines()),4)
    def test_bounded_rate_limit(self):
        starts=[]
        def transport():starts.append(self.time.now);return 429,{'error':{'message':'rate limit'}}
        with self.assertRaises(SafetyStop):self.call(transport)
        self.assertEqual(starts,[0.,2.,6.,14.])
        with self.assertRaises(SafetyStop):self.call(transport)
        self.assertEqual(len(starts),4)
    def test_rpc_rate_limit_then_success(self):
        responses=iter([(200,{'error':{'code':-32005}}),(200,{'result':'ok'})])
        self.assertEqual(self.call(lambda:next(responses)),(200,{'result':'ok'}));self.assertEqual(self.time.delays,[2.])
    def test_billing_precedes_retry_and_no_secret(self):
        secret='https://provider.test/private?key=SUPERSECRET'
        with self.assertRaises(SafetyStop):self.call(lambda:(429,{'error':{'message':'free quota exceeded '+secret}}))
        self.assertNotIn(secret,self.path.read_text());self.assertNotIn('SUPERSECRET',self.path.read_text());self.assertEqual(self.time.delays,[])
        with self.assertRaises(SafetyStop):self.call(lambda:(200,{}))
    def test_billing_fixtures(self):
        for status,body in [(402,{}),(200,'paid plan'),(200,{'error':'billing required'}),(200,'free quota exhausted'),(200,'payment required')]:
            self.assertTrue(billing_stop(status,body))
        self.assertFalse(billing_stop(200,{'result':'0x1234'}))
    def test_ledger_rejects_unsanitized_fields(self):
        with self.assertRaises(ValueError):self.ledger.append(event='request_started',method='https://secret',row_index=0,attempt=0)
        with self.assertRaises(ValueError):self.ledger.append(event='request_started',method='eth_chainId',row_index='secret',attempt=0)
        with self.assertRaises(TypeError):self.ledger.append(event='request_started',method='eth_chainId',row_index=0,attempt=0,url='secret')
        self.assertFalse(self.path.exists())
    def test_transport_exception_sanitized(self):
        def transport():raise RuntimeError('https://provider?key=SECRET')
        with self.assertRaisesRegex(SafetyStop,'details omitted') as error:self.call(transport)
        self.assertNotIn('SECRET',str(error.exception));self.assertNotIn('SECRET',self.path.read_text())
        with self.assertRaisesRegex(SafetyStop,'already stopped'):
            self.call(lambda:self.fail('Stopped gate invoked transport'))
    def test_hash_freeze_and_one_score(self):
        frozen=self.root/'input';frozen.write_bytes(b'frozen');expected={frozen:hashlib.sha256(b'frozen').hexdigest()};lock=self.root/'score.lock'
        verify_frozen_inputs(expected);acquire_score_lock(lock,expected)
        with self.assertRaises(SafetyStop):acquire_score_lock(lock,expected)
        frozen.write_bytes(b'changed')
        with self.assertRaises(SafetyStop):verify_frozen_inputs(expected)
        with self.assertRaises(SafetyStop):acquire_score_lock(self.root/'other.lock',expected)
        self.assertFalse((self.root/'other.lock').exists())

if __name__=='__main__':unittest.main()
