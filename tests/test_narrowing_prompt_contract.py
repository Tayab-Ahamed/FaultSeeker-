"""Software-only narrowing contract regressions; no model completion evidence."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.modules.setdefault('readline', None)
import pytest

from benchmark.nara_pilot_provider import ENDPOINT, MODEL, NaraPilot, StudyStop
import faultseeker.core.llm_router as router_module
from faultseeker.core.llm_router import HybridLLMRouter
from faultseeker.core.spend_guard import SpendGuard
from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
from faultseeker.prompts.function_analysis.worker_prompts import WorkerPrompts


OWNER = '0x' + '11' * 20


def narrowing_analyzer(response, created=False):
    analyzer = FunctionAnalyzer.__new__(FunctionAnalyzer)
    functions = ['0x%08x' % i for i in range(1, 7)]
    keys = functions if created else [function + '_' + OWNER for function in functions]
    candidates = {key: {'count': 1, 'calls': [], 'address': [OWNER]} for key in keys}
    analyzer.functions_to_be_inspected = {} if created else candidates
    analyzer.address_calls_with_created_contract_in_params = candidates if created else {}
    analyzer.repeated_patterns = []
    analyzer.fundflow_analysis = {'balance_change': {}}
    analyzer.function_prompts = WorkerPrompts()
    analyzer.children_call_memo = {}
    analyzer.children_call_memo_single = {}
    analyzer.trace = []
    analyzer.txn_seq = {'created_address': []}
    analyzer.potentially_vulnerable_functions = {}
    analyzer.understanding_result = ''
    prompts, inspected = [], []
    def query(prompt):
        prompts.append(prompt)
        return response(keys)
    analyzer.agent = SimpleNamespace(query=query)
    analyzer._retrieve_related_info = lambda *args: None
    analyzer._function_analysis_init = lambda: inspected.append(dict(analyzer.function_call_info_summary))
    return analyzer, keys, prompts, inspected


@pytest.mark.parametrize('created', [False, True])
def test_real_narrowing_prompt_states_exact_json_contract_without_selection_prior(created):
    analyzer, keys, prompts, inspected = narrowing_analyzer(lambda keys: keys[2:4], created)
    analyzer._review_function_calls()
    prompt = prompts[0]
    assert 'strict JSON array' in prompt
    assert 'square brackets' in prompt
    assert 'unique' in prompt
    assert 'copied exactly' in prompt
    assert 'not a valid selection' in prompt
    assert 'set' in prompt and 'object' in prompt
    assert 'markdown' in prompt and 'extra text' in prompt
    if created:
        assert 'do not append an address' in prompt
        assert [record['function'] for record in inspected] == keys[2:4]
    else:
        assert 'bare selectors' in prompt and 'missing owners' in prompt
        assert [record['address'] for record in inspected] == [OWNER, OWNER]
    # Every supplied key occurs only as evidence, not as an illustrative choice.
    assert all(prompt.count('"' + key + '"') == 1 for key in keys)


def test_valid_json_bare_selectors_are_rejected_before_function_analysis():
    analyzer, keys, prompts, inspected = narrowing_analyzer(
        lambda keys: json.loads(json.dumps([keys[0].split('_')[0]])))
    with pytest.raises(ValueError, match='unknown keys'):
        analyzer._review_function_calls()
    assert len(prompts) == 1 and inspected == []
    assert list(analyzer.functions_to_be_inspected) == keys


def test_created_function_keys_reject_appended_owner():
    analyzer, keys, prompts, inspected = narrowing_analyzer(lambda keys: [keys[0] + '_' + OWNER], True)
    with pytest.raises(ValueError, match='unknown keys'):
        analyzer._review_function_calls()
    assert len(prompts) == 1 and inspected == []
    assert list(analyzer.address_calls_with_created_contract_in_params) == keys


def test_recorded_revest_set_response_remains_rejected_after_one_offline_attempt(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    record = json.loads((root / 'reports/cohort_rebuild_v2/gateway_runs/20261016T100027-0ae94f84/calls/call-001.json').read_text(encoding='utf-8'))
    content = record['response']['choices'][0]['message']['content']
    assert content.strip().startswith('{"0xf97e7d74",')
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)
    rates = {'input': .1, 'output': .2}
    monkeypatch.setitem(router_module.COST_RATES, MODEL, rates)
    guard = SpendGuard(tmp_path / 'spend.json', pricing={MODEL: rates})
    router = HybridLLMRouter(cloud_model=MODEL, routing_strategy='cloud-only',
                            remote_model_ids=[MODEL], spend_guard=guard)
    requests = []
    def transport(url, headers, body, timeout):
        requests.append(json.loads(body))
        return 200, record['response_text'].encode('utf-8'), ENDPOINT
    pilot = NaraPilot(api_key='software-fixture-secret', router=router,
                      output_dir=tmp_path / 'calls', transport=transport)
    analyzer, keys, prompts, inspected = narrowing_analyzer(lambda keys: keys[:1])
    analyzer.agent = pilot.factory('', 'ranking_agent')
    with pytest.raises(ValueError):
        analyzer._review_function_calls()
    with pytest.raises(StudyStop):
        analyzer.agent.query('No recovery dispatch')
    assert len(requests) == pilot.calls == 1
    assert inspected == [] and list(analyzer.functions_to_be_inspected) == keys
    assert [event['event'] for event in guard.report()['events']] == ['reserve', 'settle']
    saved = json.loads((tmp_path / 'calls/call-001.json').read_text(encoding='utf-8'))
    assert saved['response']['choices'][0]['message']['content'] == content
    assert 'response_format' not in requests[0]
