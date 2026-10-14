"""Behavior of actual query-time routing with local provider doubles."""

import pytest
import io
import json

from faultseeker.core.llm_router import COST_RATES, HybridLLMRouter, build_routed_agent
from faultseeker.core.spend_guard import BudgetApprovalRequired, SpendGuard
from faultseeker.utils.agent import AnthropicAgent


class Provider:
    def __init__(self, task, model, replies):
        self.model = model
        self.memory = [{"role": "system", "content": task}]
        self.replies = replies
        self.last_usage = None

    def _send_message(self, prompt, temperature=0):
        self.memory.append({"role": "user", "content": prompt})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        self.last_usage = {"prompt_tokens": 12, "completion_tokens": 8}
        self.memory.append({"role": "assistant", "content": reply})
        return reply


def test_tier_two_good_local_result_stays_local():
    providers = {}

    def factory(task, model):
        providers.setdefault(model, Provider(task, model, ['{"confidence": 0.9, "evidence": ["trace"]}']))
        return providers[model]

    router = HybridLLMRouter(local_model="llama3:8b", cloud_model="gpt-4o-mini")
    agent = build_routed_agent("", router=router, agent_role="generation_agent",
                               system_prompt="system", provider_factory=factory)
    result = agent.query("assess function")

    assert result == {"confidence": 0.9, "evidence": ["trace"]}
    assert list(providers) == ["llama3:8b"]
    assert router.cost_summary.total_queries == 1
    assert router.cost_summary.records[0].input_tokens_est == 12


def test_tier_two_low_confidence_falls_back_and_records_both_attempts(tmp_path):
    replies = {
        "llama3:8b": ['{"confidence": 0.2, "evidence": ["weak"]}'],
        "gpt-4o-mini": ['{"confidence": 0.95, "evidence": ["trace"]}'],
    }
    providers = {}

    def factory(task, model):
        providers.setdefault(model, Provider(task, model, replies[model]))
        return providers[model]

    guard = SpendGuard(tmp_path / "ledger.json", pricing=COST_RATES)
    router = HybridLLMRouter(local_model="llama3:8b", cloud_model="gpt-4o-mini",
                             confidence_gate=0.6, spend_guard=guard)
    result = build_routed_agent("", router, "generation_agent", "system",
                                provider_factory=factory).query("assess")

    assert result["confidence"] == 0.95
    assert [record.model for record in router.cost_summary.records] == ["llama3:8b", "gpt-4o-mini"]
    assert [record.status for record in router.cost_summary.records] == ["failed", "success"]
    assert router.cost_summary.fallback_count == 1
    assert guard.report()["spent_usd"] > 0


def test_tier_one_stays_local_and_tier_three_goes_cloud(tmp_path):
    providers = []

    def factory(task, model):
        providers.append(model)
        return Provider(task, model, ['{"confidence": 0.1, "evidence": ["trace"]}'])

    guard = SpendGuard(tmp_path / "ledger.json", pricing=COST_RATES)
    router = HybridLLMRouter(local_model="llama3:8b", cloud_model="gpt-4o-mini",
                             spend_guard=guard)
    local = build_routed_agent("", router, "AddressClassifier", provider_factory=factory)
    cloud = build_routed_agent("", router, "reasoning_agent", provider_factory=factory)
    assert local.query("classify")['confidence'] == 0.1
    assert cloud.query("analyze")['confidence'] == 0.1
    assert providers == ["llama3:8b", "gpt-4o-mini"]


@pytest.mark.parametrize("bad_local", [
    '{"confidence": 0.9, "evidence": []}',
    '{"confidence": 0.9}',
    'not json',
])
def test_tier_two_bad_schema_or_evidence_falls_back(tmp_path, bad_local):
    replies = {"llama3:8b": [bad_local],
               "gpt-4o-mini": ['{"confidence": 0.9, "evidence": ["trace"]}']}

    def factory(task, model):
        return Provider(task, model, replies[model])

    router = HybridLLMRouter(local_model="llama3:8b", cloud_model="gpt-4o-mini",
                             spend_guard=SpendGuard(tmp_path / "ledger.json", pricing=COST_RATES))
    result = build_routed_agent("", router, "generation_agent",
                                provider_factory=factory).query("assess")
    assert result['evidence'] == ['trace']
    assert router.cost_summary.fallback_count == 1
    assert [r.status for r in router.cost_summary.records] == ['failed', 'success']


def test_cloud_budget_blocks_dispatch_and_local_loop_remains_free(tmp_path):
    calls = []

    def factory(task, model):
        calls.append(model)
        return Provider(task, model, ['{"confidence": 0.9, "evidence": ["trace"]}'])

    guard = SpendGuard(tmp_path / 'ledger.json', limit_usd=0.000001, pricing=COST_RATES)
    router = HybridLLMRouter(local_model="llama3:8b", cloud_model="gpt-4o-mini",
                             spend_guard=guard)
    local = build_routed_agent("", router, "AddressClassifier", provider_factory=factory)
    assert local.query("classify")['confidence'] == 0.9
    assert guard.report()['spent_usd'] == 0
    cloud = build_routed_agent("", router, "reasoning_agent", provider_factory=factory)
    with pytest.raises(BudgetApprovalRequired):
        cloud.query("analyze")
    assert router.cost_summary.cloud_queries == 0
    assert guard.report()['spent_usd'] == 0


def test_anthropic_adapter_uses_native_messages_schema_and_usage(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'local-test-key')
    captured = {}

    def transport(request, timeout):
        captured['url'] = request.full_url
        captured['headers'] = dict(request.header_items())
        captured['body'] = json.loads(request.data)
        return io.BytesIO(json.dumps({
            'content': [{'type': 'text', 'text': '{"ok": true}'}],
            'usage': {'input_tokens': 21, 'output_tokens': 7},
        }).encode())

    agent = AnthropicAgent('system', 'claude-3-5-sonnet', transport=transport)
    assert agent.query('check') == {'ok': True}
    assert captured['url'] == 'https://api.anthropic.com/v1/messages'
    assert captured['body']['system'] == 'system'
    assert captured['body']['messages'] == [{'role': 'user', 'content': 'check'}]
    assert captured['headers']['X-api-key'] == 'local-test-key'
    assert agent.last_usage == {'prompt_tokens': 21, 'completion_tokens': 7}


def test_percentage_confidence_below_gate_falls_back(tmp_path):
    replies = {"llama3:8b": ['{"confidence_score": 20, "evidence": ["weak"]}'],
               "gpt-4o-mini": ['{"confidence": 0.8, "evidence": ["trace"]}']}
    router = HybridLLMRouter(local_model='llama3:8b', cloud_model='gpt-4o-mini',
                             spend_guard=SpendGuard(tmp_path / 'ledger.json', pricing=COST_RATES))
    agent = build_routed_agent('', router, 'generation_agent', provider_factory=lambda task, model:
                               Provider(task, model, replies[model]))
    assert agent.query('assess')['confidence'] == 0.8
    assert router.cost_summary.fallback_count == 1


def test_failed_cloud_attempt_is_recorded_and_reserved_cost_is_kept(tmp_path):
    guard = SpendGuard(tmp_path / 'ledger.json', pricing=COST_RATES)
    router = HybridLLMRouter(local_model='llama3:8b', cloud_model='gpt-4o-mini',
                             spend_guard=guard, track_cost=False)
    agent = build_routed_agent('', router, 'reasoning_agent', provider_factory=lambda task, model:
                               Provider(task, model, [RuntimeError('provider unavailable')]))
    with pytest.raises(RuntimeError, match='provider unavailable'):
        agent.query('analyze')
    assert router.cost_summary.cloud_queries == 1
    assert router.cost_summary.records[0].status == 'failed'
    assert router.cost_summary.records[0].usage_source == 'reservation'
    assert guard.report()['spent_usd'] == pytest.approx(router.cost_summary.total_cost_usd)


def test_sdk_cannot_retry_paid_calls_behind_budget_accounting(monkeypatch):
    from types import SimpleNamespace
    from faultseeker.utils.agent import GPTAgent
    options = []
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))],
                                 usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2))
    def client(**kwargs):
        options.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: completion)))
    monkeypatch.setenv('OPENAI_API_KEY', 'local-fixture-key')
    monkeypatch.setattr('faultseeker.utils.agent.OpenAI', client)
    GPTAgent('system', 'gpt-4o-mini')._send_message('hello')
    assert options[0]['max_retries'] == 0


def test_exported_cost_summary_contains_every_attempt_for_production_measurement():
    router = HybridLLMRouter(local_model='llama3:8b', cloud_model='gpt-4o-mini', track_cost=True)
    router.record_query('llama3:8b', 2, prompt_length=10, response_length=20, force=True)
    summary = router.get_cost_summary()
    assert len(summary['records']) == 1
    assert summary['records'][0]['model'] == 'llama3:8b'


def test_child_filter_can_return_empty_selection_without_being_a_provider_failure():
    router = HybridLLMRouter(local_model='llama3:8b',cloud_model='gpt-4o-mini')
    agent = build_routed_agent('',router,'children_call_filtering',provider_factory=lambda task,model:
                               Provider(task,model,['[]']))
    assert agent.query('No child needs investigation') == []
    assert router.cost_summary.records[0].status == 'success'


@pytest.mark.parametrize('model,expected',[
    ('gpt-4o-mini','GPTAgent'),('grok-3-mini','UniversalAgent'),
    ('qwen-plus','UniversalAgent'),('gemini-2.0-flash','UniversalAgent'),
    ('claude-3-5-sonnet','AnthropicAgent'),('llama3:8b','OllmaAgent')])
def test_all_six_provider_families_construct_the_correct_adapter(monkeypatch,model,expected):
    from faultseeker.utils.agent import build_provider_agent
    for name in ('OPENAI_API_KEY','XAI_API_KEY','DASHSCOPE_API_KEY','GOOGLE_API_KEY','ANTHROPIC_API_KEY'):
        monkeypatch.setenv(name,'local-adapter-fixture')
    agent = build_provider_agent('system',model)
    assert type(agent).__name__ == expected
    assert agent.memory == [{'role':'system','content':'system'}]
