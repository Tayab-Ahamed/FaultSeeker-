"""Remote aliases must retain cloud budget and execution policies."""
import sys
sys.modules['readline']=None
from types import SimpleNamespace
import pytest
import json

def test_declared_remote_alias_is_not_local():
    from faultseeker.core.llm_router import HybridLLMRouter
    router=HybridLLMRouter(cloud_model='agnes-2.5-flash',remote_model_ids={'agnes-2.5-flash'})
    assert router._is_local_model('agnes-2.5-flash') is False
    assert router._is_local_model('phi3:mini') is True

def test_function_iteration_policy_uses_router_remote_identity():
    from faultseeker.core.llm_router import HybridLLMRouter
    from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
    router=HybridLLMRouter(cloud_model='agnes-2.5-flash',remote_model_ids={'agnes-2.5-flash'})
    analyzer=FunctionAnalyzer(model='agnes-2.5-flash',router=router,agent_factory=lambda task,role:object())
    assert analyzer._uses_cloud_model() is True

@pytest.mark.parametrize("provider", ["universal", "gpt", "anthropic"])
def test_universal_transport_preserves_source_prompt_tail(monkeypatch,provider):
    from faultseeker.utils import agent
    sent=[]
    def create(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))],usage=SimpleNamespace(prompt_tokens=3000,completion_tokens=2))
    monkeypatch.setattr(agent,'OpenAI',lambda **kwargs:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    if provider=='universal':
        actual=agent.UniversalAgent('system','agnes-2.5-flash',base_url='https://example.invalid/v1',api_key='unused-offline')
    elif provider=='gpt':
        monkeypatch.setenv('OPENAI_API_KEY','unused-offline')
        actual=agent.GPTAgent('system','gpt-4o-mini')
    else:
        monkeypatch.setenv('ANTHROPIC_API_KEY','unused-offline')
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps({'content':[{'type':'text','text':'{}'}],'usage':{'input_tokens':3000,'output_tokens':2}}).encode()
        def transport(request,timeout):
            sent.append(json.loads(request.data));return Response()
        actual=agent.AnthropicAgent('system','claude-test',transport=transport)
    prompt='x'*12000+'SOURCE_TAIL_MUST_REACH_PROVIDER'
    actual._send_message(prompt)
    assert sent[0]['messages'][-1]['content']==prompt


def test_remote_alias_reserves_before_dispatch_and_denies_over_cap(tmp_path,monkeypatch):
    from faultseeker.core import llm_router
    from faultseeker.core.spend_guard import SpendGuard,BudgetApprovalRequired
    model='agnes-2.5-flash';rates={'input':0.1,'output':0.2}
    monkeypatch.setitem(llm_router.COST_RATES,model,rates)
    guard=SpendGuard(tmp_path/'ledger.json',limit_usd=1,pricing={model:rates})
    calls=[]
    class Provider:
        memory=[]
        def _send_message(self,prompt,temperature):
            assert guard.report()['reserved_usd']>0
            calls.append(prompt);self.last_usage={'prompt_tokens':10,'completion_tokens':5}
            return '{"evidence":"Actual fixture transport boundary","confidence":0.8}'
    router=llm_router.HybridLLMRouter(cloud_model=model,routing_strategy='cloud-only',spend_guard=guard,remote_model_ids={model})
    agent=llm_router.build_routed_agent(model,router=router,agent_role='ranking_agent',provider_factory=lambda task,name:Provider())
    agent.query('first')
    assert router.cost_summary.cloud_queries==1 and router.cost_summary.local_queries==0
    assert guard.report()['spent_usd']>0
    guard.limit_usd=guard.report()['spent_usd']
    with pytest.raises(BudgetApprovalRequired):agent.query('must never dispatch')
    assert calls==['first']


def test_cloud_only_alias_uses_cloud_prompts_not_local_simplification():
    from faultseeker.core.llm_router import HybridLLMRouter
    from faultseeker.function_analysis.function_analyzer import FunctionAnalyzer
    from faultseeker.prompts.function_analysis import WorkerPrompts,VulnerabilityAnalysisPrompts
    router=HybridLLMRouter(local_model='phi3:mini',cloud_model='agnes-2.5-flash',routing_strategy='cloud-only',remote_model_ids={'agnes-2.5-flash'})
    analyzer=FunctionAnalyzer(model='agnes-2.5-flash',router=router,agent_factory=lambda task,role:object())
    assert type(analyzer.function_prompts) is WorkerPrompts
    assert type(analyzer.vulnerability_prompts) is VulnerabilityAnalysisPrompts
