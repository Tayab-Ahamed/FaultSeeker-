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
