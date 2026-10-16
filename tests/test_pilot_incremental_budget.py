"""An approved batch can impose a smaller cap on the shared cumulative ledger."""
import sys
sys.modules['readline']=None
import pytest
from scripts.run_train_gateway_pilot import approved_budget_limit
from faultseeker.core.spend_guard import SpendGuard,BudgetApprovalRequired

def test_batch_budget_is_relative_to_actual_shared_spend_and_capped_globally():
 assert approved_budget_limit({'max_incremental_estimated_usd':.2},{'spent_usd':1.9})==pytest.approx(2.1)
 assert approved_budget_limit({'max_incremental_estimated_usd':.2},{'spent_usd':9.9})==10
 assert approved_budget_limit({}, {'spent_usd':1.9})==10

@pytest.mark.parametrize('value',[None,True,0,-1,float('nan'),float('inf'),'0.2',11])
def test_invalid_batch_amount_is_rejected(value):
 with pytest.raises(ValueError):approved_budget_limit({'max_incremental_estimated_usd':value},{'spent_usd':1.9})

@pytest.mark.parametrize('value',[None,True,-1,float('nan'),float('inf'),'1.9',11])
def test_invalid_cumulative_spend_is_rejected(value):
 with pytest.raises(ValueError):approved_budget_limit({'max_incremental_estimated_usd':.2},{'spent_usd':value})

def test_real_guard_blocks_next_request_before_dispatch_when_incremental_cap_exhausted(tmp_path):
 model='offline-budget-model';rates={model:{'input':1,'output':1}}
 guard=SpendGuard(tmp_path/'ledger.json',pricing=rates)
 first=guard.reserve(model,100000,0);guard.settle(first,100000,0)
 guard.limit_usd=approved_budget_limit({'max_incremental_estimated_usd':.2},guard.report())
 second=guard.reserve(model,150000,0);guard.settle(second,150000,0)
 before=guard.report()
 with pytest.raises(BudgetApprovalRequired):guard.reserve(model,100000,0)
 assert guard.report()['events']==before['events']
 assert guard.report()['spent_usd']==pytest.approx(.25)
