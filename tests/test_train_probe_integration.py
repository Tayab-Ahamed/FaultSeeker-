"""Actual recovered provider traces enter production without invented storage."""
import sys
sys.modules['readline']=None

def test_actual_recovered_train_traces_preserve_canonical_identity():
    from scripts.integrate_train_trace_probes import integrate
    records=integrate(write_index=False)
    assert {r['identity'].split(':')[0] for r in records}=={'fantom','gnosis'}
    assert all(r['frame_count']>1 for r in records)
    assert all(r['storage_trace_complete'] is False for r in records)
    assert all(r['trace_identity_verified'] is True for r in records)
