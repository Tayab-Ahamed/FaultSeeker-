from datetime import datetime,timezone
import pytest
from benchmark.pilot_token_guard import DailyTokenGuard,DailyTokenLimitReached

def guard(tmp_path,clock=None):return DailyTokenGuard(tmp_path/'daily.json',limit_tokens=100,now_utc=clock or (lambda:datetime(2026,10,16,tzinfo=timezone.utc)))

def test_cross_instance_reservations_block_before_dispatch(tmp_path):
 a=guard(tmp_path);b=guard(tmp_path);a.reserve(60,20)
 with pytest.raises(DailyTokenLimitReached):b.reserve(21,0)
 assert b.report()['reserved']==80 and b.report()['remaining']==20

def test_actual_usage_settlement_not_double_counted(tmp_path):
 a=guard(tmp_path);r=a.reserve(60,20);assert a.settle(r,10,5)==15
 assert a.report()['used']==15 and a.report()['reserved']==0 and a.report()['remaining']==85
 with pytest.raises(ValueError):a.settle(r,10,5)

def test_missing_receipt_charges_full_reservation(tmp_path):
 a=guard(tmp_path);r=a.reserve(60,20);assert a.settle(r,failed=True)==80
 assert a.report()['used']==80

@pytest.mark.parametrize('p,c',[(True,3),(-1,3),(float('nan'),3),(1.2,3),('4',3),(None,3),(3,None)])
def test_malformed_usage_books_full_then_rejects(tmp_path,p,c):
 a=guard(tmp_path);r=a.reserve(60,20)
 with pytest.raises(ValueError):a.settle(r,p,c)
 assert a.report()['used']==80 and a.report()['reserved']==0

def test_usage_above_reservation_blocks_next_call(tmp_path):
 a=guard(tmp_path);r=a.reserve(20,20);assert a.settle(r,90,20)==110
 with pytest.raises(DailyTokenLimitReached):a.reserve(1,0)
 assert a.report()['remaining']==0

def test_utc_rollover_retains_original_reservation_and_events(tmp_path):
 now=[datetime(2026,10,16,23,59,tzinfo=timezone.utc)];a=guard(tmp_path,lambda:now[0]);r=a.reserve(60,20)
 now[0]=datetime(2026,10,17,tzinfo=timezone.utc)
 assert a.report()['used']==0 and a.report()['reserved']==0
 a.settle(r,10,5)
 report=a.report();assert report['used']==0 and report['buckets']['2026-10-16']['used']==15
 assert report['time_zone']=='UTC'

def test_import_is_idempotent_and_conflict_rejected(tmp_path):
 a=guard(tmp_path);e={'path':'calls/1.json','sha256':'a'*64}
 assert a.import_usage_once('historical-1','2026-10-16',10,5,e)==15
 assert a.import_usage_once('historical-1','2026-10-16',10,5,e)==0
 assert a.report()['used']==15
 with pytest.raises(ValueError):a.import_usage_once('historical-1','2026-10-16',11,5,e)

@pytest.mark.parametrize('value',[True,-1,1.2,'2',None])
def test_invalid_reservation_rejected(tmp_path,value):
 with pytest.raises(ValueError):guard(tmp_path).reserve(value,1)

def test_corrupt_ledger_fails_closed(tmp_path):
 (tmp_path/'daily.json').write_text('{}',encoding='utf-8')
 with pytest.raises(ValueError):guard(tmp_path).report()


def test_concurrent_instances_cannot_overshoot(tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 def reserve_one(_):
  try:guard(tmp_path).reserve(11,0);return True
  except DailyTokenLimitReached:return False
 with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(reserve_one,range(20)))
 assert sum(results)==9 and guard(tmp_path).report()['reserved']==99

def test_unsettled_previous_day_is_retained(tmp_path):
 now=[datetime(2026,10,16,23,59,tzinfo=timezone.utc)];a=guard(tmp_path,lambda:now[0]);r=a.reserve(60,20)
 now[0]=datetime(2026,10,17,tzinfo=timezone.utc);a.reserve(10,10)
 report=a.report();assert report['buckets']['2026-10-16']['reserved']==80
 assert r in report['reservations'] and report['reserved']==20

def test_import_allocation_and_used_history_retained(tmp_path):
 a=guard(tmp_path);e={'path':'historical.json','sha256':'b'*64}
 assert a.import_allocation_once('unknown-receipt','2026-10-16',80,e)==80
 assert a.import_allocation_once('unknown-receipt','2026-10-16',80,e)==0
 assert a.report()['used']==80
 assert a.report()['events'][0]['usage_source']=='conservative-allocation'
