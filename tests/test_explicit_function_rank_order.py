"""Production rank serialization cannot confuse address priority and function rank."""
import sys
sys.modules['readline']=None

def test_actual_revest_ranker_exports_function_identity_and_stable_count_order(tmp_path):
    from scripts.run_train_production import observe_stage_one, ROOT
    key='eth:0xe0b0c2672b760bef4e2851e91c69c8c0ad135c6987bbf1f43f5846d89e691428'
    observed=observe_stage_one(ROOT,key,tmp_path)
    ordered=observed['ranking']['ranked_functions']
    assert ordered
    assert [r['rank'] for r in ordered]==list(range(1,len(ordered)+1))
    assert len({(r['code_address'],r['function']) for r in ordered})==len(ordered)
    assert [
        (-r['path_concentration'], r['terminal_fanout'],
         -max(map(len, r['supporting_call_depths']), default=0), -r['count'])
        for r in ordered
    ] == sorted([
        (-r['path_concentration'], r['terminal_fanout'],
         -max(map(len, r['supporting_call_depths']), default=0), -r['count'])
        for r in ordered
    ])
    assert any(r['code_address']=='0x2320a28f52334d62622cc2eafa15de55f9987ed9' and r['function']=='0x5dcb7ab2' for r in ordered)
    assert all(r['tie_policy']=='call-path concentration desc; terminal fanout asc; max depth desc; count desc; stable candidate encounter order' for r in ordered)
