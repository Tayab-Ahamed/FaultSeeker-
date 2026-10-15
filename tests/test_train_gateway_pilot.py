import sys
sys.modules['readline']=None
import pytest

def test_pilot_refuses_execution_without_explicit_live_flag():
    from scripts.run_train_gateway_pilot import run
    with pytest.raises(ValueError,match='--live'):run(live=False)

def test_actual_pricing_and_membership_inputs_fail_closed():
    from scripts.run_train_gateway_pilot import configuration,ROOT
    protocol,rates=configuration(ROOT)
    assert len(protocol['train_identities'])==2
    assert rates['input']>0 and rates['output']>0
    assert protocol['routing'].startswith('cloud-only')
    assert protocol['max_calls']==20


def test_approved_pilot_dispatch_permit_cannot_be_silently_reused(tmp_path):
    from scripts.run_train_gateway_pilot import claim_dispatch
    path=tmp_path/'permit.json'
    claim_dispatch(path,{'max_completion_requests':20},'first')
    with pytest.raises(FileExistsError):claim_dispatch(path,{'max_completion_requests':20},'second')


def test_reapproval_cap_is_bounded_and_pending_scope_cannot_dispatch():
    from scripts.run_train_gateway_pilot import approved_call_cap
    approval={'approved':True,'max_completion_requests':14,'stop_on_any_error':True,
              'destination':'https://router.bynara.id/v1/chat/completions',
              'protocol':{'path':'p','sha256':'h'}}
    assert approved_call_cap(approval,approval['protocol'])==14
    for changes in ({'approved':False},{'max_completion_requests':21},{'max_completion_requests':True},
                    {'stop_on_any_error':False},{'destination':'https://other.example'}):
        with pytest.raises(ValueError):approved_call_cap(dict(approval,**changes),approval['protocol'])
    with pytest.raises(ValueError):approved_call_cap(approval,{'path':'changed','sha256':'h'})


def test_followup_pilot_keeps_combined_twenty_request_ceiling():
    from scripts.run_train_gateway_pilot import approved_call_cap
    approval={'approved':True,'max_completion_requests':14,'stop_on_any_error':True,
              'destination':'https://router.bynara.id/v1/chat/completions','protocol':{},
              'previous_completion_requests':6,'aggregate_pilot_limit':20}
    assert approved_call_cap(approval,{})==14
    with pytest.raises(ValueError):approved_call_cap(dict(approval,max_completion_requests=15),{})
