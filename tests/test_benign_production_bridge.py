"""Captured distinct controls exercise production without inferred completeness."""
import sys
sys.modules['readline']=None

def test_control_admissions_revalidate_and_execute_actual_stage_one(tmp_path):
    from scripts.run_benign_controls import load_controls,observe_control,ROOT
    records=load_controls(ROOT)
    assert len(records)==32
    assert len({r['transaction']['hash'] for r in records})==32
    observed=observe_control(next(r for r in records if r['call_trace']['available']),tmp_path,ROOT)
    assert observed['network_attempts']==0
    assert observed['coverage']['multi_tx_context_complete'] is False
    assert observed['coverage']['token_flow_complete'] is False
    assert observed['stage2_executed'] is False
    assert observed['verdict'] in {'BENIGN','UNCERTAIN','EXPLOIT'}
