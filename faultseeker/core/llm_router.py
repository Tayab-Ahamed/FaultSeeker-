"""
Hybrid LLM Router for FaultSeeker++
Research Gap 1: Cloud Dependency + Gap 6: High Infrastructure Cost

Routes LLM queries between local (Ollama) and cloud (OpenAI) models
based on task complexity, using 3-tier classification:
  - Tier 1 (Simple): Local model only (zero API cost)
  - Tier 2 (Moderate): Local with cloud fallback
  - Tier 3 (Complex): Cloud model directly

Also tracks per-query cost for cost optimization reporting.
"""

import json
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from faultseeker.utils.agent import OllmaAgent, GPTAgent


# Cost rates per 1M tokens (USD)
COST_RATES = {
    # OpenAI
    'gpt-4o':           {'input': 2.50,  'output': 10.00},
    'gpt-4o-mini':      {'input': 0.15,  'output': 0.60},
    'gpt-4.1':          {'input': 2.00,  'output': 8.00},
    'gpt-4.1-mini':     {'input': 0.40,  'output': 1.60},
    'gpt-4.1-nano':     {'input': 0.10,  'output': 0.40},
    'o3-mini':          {'input': 1.10,  'output': 4.40},
    # Anthropic native Messages API
    'claude-3-5-sonnet': {'input': 3.00, 'output': 15.00},
    # xAI Grok
    'grok-3':           {'input': 3.00,  'output': 15.00},
    'grok-3-mini':      {'input': 0.30,  'output': 0.50},
    'grok-2':           {'input': 2.00,  'output': 10.00},
    'grok-2-mini':      {'input': 0.20,  'output': 0.40},
    # Alibaba Qwen (DashScope)
    'qwen-max':         {'input': 0.40,  'output': 1.20},
    'qwen-plus':        {'input': 0.08,  'output': 0.26},
    'qwen-turbo':       {'input': 0.02,  'output': 0.06},
    'qwen-long':        {'input': 0.005, 'output': 0.02},
    # Google Gemini
    'gemini-2.0-flash': {'input': 0.10,  'output': 0.40},
    'gemini-1.5-pro':   {'input': 1.25,  'output': 5.00},
    'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},
    # Local models are free
}

# Agent role → default tier mapping (from plan)
AGENT_TIER_MAP = {
    'AddressClassifier': 1,         # Simple classification
    'children_call_filtering': 1,   # Simple filtering
    'generation_agent': 2,          # Task generation (moderate)
    'organization_agent': 2,        # Info organization (moderate)
    'ranking_agent': 2,             # Function ranking (moderate)
    'reasoning_agent': 3,           # Deep analysis (complex)
    'processing_agent': 3,          # Task processing (complex)
}

# Complexity keywords for heuristic classification
COMPLEXITY_KEYWORDS = {
    'high': ['analyze', 'vulnerability', 'exploit', 'cross-contract',
             'reentrancy', 'attack', 'investigate', 'reasoning'],
    'low': ['classify', 'format', 'extract', 'parse', 'list', 'filter',
            'categorize', 'label', 'identify'],
}


@dataclass
class CostRecord:
    """Tracks cost of a single LLM query."""
    model: str
    tier: int
    is_local: bool
    input_tokens_est: int = 0
    output_tokens_est: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    fallback_used: bool = False
    status: str = 'success'
    usage_source: str = 'estimate'
    error: str = ''


@dataclass
class CostSummary:
    """Aggregated cost summary across all queries."""
    total_queries: int = 0
    local_queries: int = 0
    cloud_queries: int = 0
    fallback_count: int = 0
    total_cost_usd: float = 0.0
    estimated_cloud_only_cost: float = 0.0  # What it would've cost without routing
    savings_usd: float = 0.0
    savings_percent: float = 0.0
    records: List[CostRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_queries': self.total_queries,
            'local_queries': self.local_queries,
            'cloud_queries': self.cloud_queries,
            'fallback_count': self.fallback_count,
            'total_cost_usd': self.total_cost_usd,
            'estimated_cloud_only_cost': self.estimated_cloud_only_cost,
            'savings_usd': self.savings_usd,
            'savings_percent': round(self.savings_percent, 1),
            'pricing_units': 'USD per 1,000,000 input or output tokens',
            'pricing_verified_at': None,
            'records': [asdict(record) for record in self.records],
        }


class HybridLLMRouter:
    """
    Intelligent LLM query router implementing 3-tier complexity-based routing.

    Integrates with FaultSeeker's existing build_agent() pattern by providing
    a route() method that selects the appropriate model for each query.
    """

    def __init__(
        self,
        local_model: str = 'llama3:8b',
        cloud_model: str = 'gpt-4o-mini',
        confidence_gate: float = 0.6,
        track_cost: bool = True,
        routing_strategy: str = 'hybrid',  # 'local-first', 'cloud-first', 'hybrid', 'cloud-only'
        ablation: Any = None,
        cost_tracker: Any = None,
        spend_guard: Any = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.local_model = local_model
        self.cloud_model = cloud_model
        self.confidence_gate = confidence_gate
        self.track_cost = track_cost
        self.routing_strategy = routing_strategy

        from faultseeker.research.ablation import AblationConfig
        self.ablation = ablation or AblationConfig.full_system()
        self.cost_tracker = cost_tracker
        self.spend_guard = spend_guard

        # Cost tracking
        self.cost_summary = CostSummary()

    def select_model(
        self,
        agent_role: str = '',
        prompt_text: str = '',
        tier_override: Optional[int] = None,
    ) -> str:
        """
        Select the appropriate model for a query.

        Args:
            agent_role: Name/role of the agent making the query
            prompt_text: The prompt text (used for heuristic classification)
            tier_override: Force a specific tier (1, 2, or 3)

        Returns:
            Model name string suitable for build_agent()
        """
        # Ablation: disabling LLM routing means every query goes to the cloud
        # model, which is what "no routing" actually is. The tier heuristic is
        # bypassed entirely rather than having its score adjusted.
        if not self.ablation.enabled('llm_routing'):
            return self.cloud_model

        if self.routing_strategy == 'cloud-only':
            return self.cloud_model

        # Determine tier
        if tier_override:
            tier = tier_override
        elif agent_role in AGENT_TIER_MAP:
            tier = AGENT_TIER_MAP[agent_role]
        else:
            tier = self._classify_complexity(prompt_text)

        # Route based on tier
        if tier == 1:
            return self.local_model
        elif tier == 2:
            if self.routing_strategy == 'cloud-first':
                return self.cloud_model
            return self.local_model  # Local first, fallback handled by caller
        else:  # tier 3
            return self.cloud_model

    def get_tier(self, agent_role: str = '', prompt_text: str = '') -> int:
        """Get the complexity tier for a query."""
        if agent_role in AGENT_TIER_MAP:
            return AGENT_TIER_MAP[agent_role]
        return self._classify_complexity(prompt_text)

    def should_fallback_to_cloud(self, tier: int) -> bool:
        """Check if a tier 2 query should fall back to cloud."""
        return tier == 2

    def record_query(
        self,
        model: str,
        tier: int,
        prompt_length: int = 0,
        response_length: int = 0,
        duration_ms: float = 0,
        fallback_used: bool = False,
        agent_role: str = '',
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        status: str = 'success',
        usage_source: str = 'estimate',
        error: str = '',
        cost_usd_override: Optional[float] = None,
        force: bool = False,
    ):
        """Record a query for cost tracking."""
        if not self.track_cost and not force:
            return

        is_local = self._is_local_model(model)

        # Use actual token counts if provided, otherwise estimate (~4 chars per token)
        if input_tokens is None:
            input_tokens = prompt_length // 4
        if output_tokens is None:
            output_tokens = response_length // 4

        # Calculate cost
        cost = 0.0
        if not is_local:
            if model not in COST_RATES:
                raise ValueError(f'Unknown cloud pricing for {model}; no call may be treated as free')
            rates = COST_RATES[model]
            cost = (input_tokens * rates['input'] + output_tokens * rates['output']) / 1_000_000
        if cost_usd_override is not None:
            cost = cost_usd_override

        record = CostRecord(
            model=model,
            tier=tier,
            is_local=is_local,
            input_tokens_est=input_tokens,
            output_tokens_est=output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            fallback_used=fallback_used,
            status=status,
            usage_source=usage_source,
            error=error,
        )

        self.cost_summary.records.append(record)
        self.cost_summary.total_queries += 1
        self.cost_summary.total_cost_usd += cost

        if is_local:
            self.cost_summary.local_queries += 1
        else:
            self.cost_summary.cloud_queries += 1
        if fallback_used:
            self.cost_summary.fallback_count += 1

        # Bridge into the research CostTracker so paper section 6.7 numbers come
        # from real calls instead of hardcoded constants.
        if self.cost_tracker is not None:
            if (not is_local and hasattr(self.cost_tracker, 'pricing') and
                    model not in self.cost_tracker.pricing):
                self.cost_tracker.pricing[model] = {
                    'prompt': COST_RATES[model]['input'],
                    'completion': COST_RATES[model]['output'],
                }
            self.cost_tracker.record_llm_call(
                stage=agent_role or 'llm_query',
                tier='local' if is_local else 'cloud',
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                latency_secs=duration_ms / 1000.0,
                status=status,
                usage_source=usage_source,
                cost_usd_override=cost_usd_override,
            )

        # Estimate what cloud-only would cost
        if model in COST_RATES:
            cloud_rates = COST_RATES.get(self.cloud_model, COST_RATES.get('gpt-4o-mini', {}))
            cloud_cost = (input_tokens * cloud_rates.get('input', 0.15) +
                         output_tokens * cloud_rates.get('output', 0.60)) / 1_000_000
            self.cost_summary.estimated_cloud_only_cost += cloud_cost
        elif is_local:
            # If local, the cloud alternative would have cost something
            cloud_rates = COST_RATES.get(self.cloud_model, COST_RATES.get('gpt-4o-mini', {}))
            cloud_cost = (input_tokens * cloud_rates.get('input', 0.15) +
                         output_tokens * cloud_rates.get('output', 0.60)) / 1_000_000
            self.cost_summary.estimated_cloud_only_cost += cloud_cost

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get the current cost summary."""
        s = self.cost_summary
        s.savings_usd = s.estimated_cloud_only_cost - s.total_cost_usd
        if s.estimated_cloud_only_cost > 0:
            s.savings_percent = (s.savings_usd / s.estimated_cloud_only_cost) * 100
        return s.to_dict()

    def print_cost_report(self):
        """Print a formatted cost report to stdout."""
        summary = self.get_cost_summary()
        print("\n💰 Cost Report:")
        print(f"   Queries: {summary['total_queries']} total "
              f"({summary['local_queries']} local, {summary['cloud_queries']} cloud)")
        print(f"   Fallbacks: {summary['fallback_count']}")
        print(f"   Actual cost:     ${summary['total_cost_usd']:.8f}")
        print(f"   Cloud-only cost: ${summary['estimated_cloud_only_cost']:.8f}")
        print(f"   Savings:         ${summary['savings_usd']:.8f} "
              f"({summary['savings_percent']:.0f}%)")

    # ─── Private ──────────────────────────────────────────────────────

    def _classify_complexity(self, prompt_text: str) -> int:
        """Heuristic complexity classification based on prompt content."""
        text_lower = prompt_text.lower()
        prompt_len = len(prompt_text)

        high_score = sum(1 for kw in COMPLEXITY_KEYWORDS['high'] if kw in text_lower)
        low_score = sum(1 for kw in COMPLEXITY_KEYWORDS['low'] if kw in text_lower)

        # Long prompts with complex keywords → tier 3
        if (high_score >= 2 and prompt_len > 2000) or high_score >= 3:
            return 3
        # Short prompts with simple keywords → tier 1
        elif low_score >= 2 and prompt_len < 1000:
            return 1
        # Everything else → tier 2
        else:
            return 2

    def _is_local_model(self, model: str) -> bool:
        """Check if a model is a local model (not a cloud API)."""
        cloud_prefixes = ('gpt-', 'o1-', 'o3-', 'o4-',
                          'claude-', 'grok-', 'qwen-', 'gemini-')
        return not any(model.startswith(p) for p in cloud_prefixes)


class RoutedAgent:
    """Drop-in agent that chooses the provider for every query."""

    def __init__(self, system_prompt, router, agent_role, provider_factory):
        self.system_prompt = system_prompt
        self.router = router
        self.agent_role = agent_role
        self.provider_factory = provider_factory
        self.providers = {}
        self.memory = [{"role": "system", "content": system_prompt}]
        self.model = router.select_model(agent_role=agent_role)

    def reset_memory(self):
        self.memory = [{"role": "system", "content": self.system_prompt}]
        self.providers.clear()

    def _provider(self, model):
        if model not in self.providers:
            self.providers[model] = self.provider_factory(self.system_prompt, model)
        return self.providers[model]

    @staticmethod
    def _confidence(value):
        if isinstance(value, dict):
            for key in ('confidence', 'confidence_score'):
                if key in value:
                    raw = value[key]
                    if isinstance(raw, list) and raw:
                        raw = raw[0]
                    try:
                        number = float(raw)
                        if not math.isfinite(number) or number < 0 or number > 100:
                            return None
                        return number / 100 if number > 1 else number
                    except (TypeError, ValueError):
                        return None
            for child in value.values():
                score = RoutedAgent._confidence(child)
                if score is not None:
                    return score
        return None

    @staticmethod
    def _valid_evidence(value):
        if isinstance(value, dict):
            for key in ('evidence', 'evidences'):
                if key in value and not value[key]:
                    return False
            return all(RoutedAgent._valid_evidence(v) for v in value.values())
        if isinstance(value, list):
            return all(RoutedAgent._valid_evidence(v) for v in value)
        return True

    @staticmethod
    def _has_evidence(value):
        if isinstance(value, dict):
            if any(value.get(key) for key in ('evidence', 'evidences')):
                return True
            return any(RoutedAgent._has_evidence(child) for child in value.values())
        if isinstance(value, list):
            return any(RoutedAgent._has_evidence(child) for child in value)
        return False

    def _attempt(self, model, prompt, temperature, output_format, tier, fallback,
                 enforce_confidence=False):
        provider = self._provider(model)
        started = time.perf_counter()
        raw = ''
        failure = None
        reservation = None
        guard = getattr(self.router, 'spend_guard', None)
        if not self.router._is_local_model(model):
            if guard is None:
                from faultseeker.core.spend_guard import SpendGuard
                guard = self.router.spend_guard = SpendGuard(pricing=COST_RATES)
            # UTF-8 byte length is a conservative input token bound; provider
            # adapters enforce the output cap used by this reservation.
            history = getattr(provider, 'memory', self.memory)
            input_bound = 2 * (len(json.dumps(history).encode('utf-8')) +
                               len(json.dumps(prompt).encode('utf-8'))) + 1024
            reservation = guard.reserve(model, input_bound, 4096)
        try:
            provider.last_usage = None
            raw = provider._send_message(prompt, temperature)
            if not isinstance(raw, str) or not raw.strip() or raw == 'An error occurred.':
                raise ValueError('Provider returned no usable response')
            if output_format == 'str':
                result = raw
            else:
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    if not hasattr(provider, '_extract_json'):
                        raise
                    result = provider._extract_json(raw)
                empty_child_selection = self.agent_role == 'children_call_filtering' and result == []
                if not isinstance(result, (dict, list)) or (not result and not empty_child_selection):
                    raise ValueError('Invalid response schema')
            if not self._valid_evidence(result):
                raise ValueError('Invalid evidence')
            if enforce_confidence:
                if not self._has_evidence(result):
                    raise ValueError('Local response lacks supporting evidence')
                confidence = self._confidence(result)
                if confidence is None or confidence < self.router.confidence_gate:
                    raise ValueError('Local confidence below routing threshold or unavailable')
        except Exception as exc:
            failure = exc
            result = None
        usage = getattr(provider, 'last_usage', None) or {}
        input_tokens = usage.get('prompt_tokens')
        output_tokens = usage.get('completion_tokens')
        settled_cost = None
        if reservation is not None:
            try:
                settled_cost = guard.settle(reservation, input_tokens, output_tokens,
                                            failed=failure is not None)
            except ValueError as usage_error:
                # An invalid provider usage object cannot erase the reserved
                # charge or leave this dispatched attempt unrecorded.
                input_tokens = output_tokens = None
                failure = failure or usage_error
                settled_cost = guard.settle(reservation, failed=True)
        self.router.record_query(
            model=model, tier=tier, prompt_length=len(prompt), response_length=len(raw),
            duration_ms=(time.perf_counter() - started) * 1000,
            fallback_used=fallback, agent_role=self.agent_role,
            input_tokens=input_tokens, output_tokens=output_tokens,
            status='failed' if failure else 'success',
            usage_source=('provider' if input_tokens is not None and output_tokens is not None
                          else 'reservation' if reservation is not None else 'estimate'),
            error=str(failure) if failure else '',
            cost_usd_override=settled_cost,
            force=True,
        )
        if failure:
            raise failure
        self.model = model
        self.memory.append({'role': 'user', 'content': prompt})
        self.memory.append({'role': 'assistant', 'content': raw})
        return result

    def query(self, user_message, temperature=0, format='json'):
        tier = self.router.get_tier(agent_role=self.agent_role, prompt_text=user_message)
        model = self.router.select_model(agent_role=self.agent_role, prompt_text=user_message)
        if model != self.router.local_model:
            return self._attempt(model, user_message, temperature, format, tier, False)
        try:
            result = self._attempt(model, user_message, temperature, format, tier, False,
                                   enforce_confidence=(tier == 2 and
                                                       self.router.should_fallback_to_cloud(tier)))
            return result
        except Exception:
            if tier != 2:
                raise
        return self._attempt(self.router.cloud_model, user_message, temperature, format, tier, True)


def build_routed_agent(
    model_name: str,
    router: Optional[HybridLLMRouter] = None,
    agent_role: str = '',
    system_prompt: str = '',
    provider_factory: Any = None,
) -> Any:
    """
    Build an LLM agent with optional routing.

    Drop-in enhancement for FaultSeeker's build_agent() function.
    If a router is provided, it selects the model; otherwise uses the
    given model_name directly.

    Uses build_provider_agent() to correctly route:
      gpt-*, o1-*, o3-*, o4-*  → GPTAgent  (OpenAI)
      gemini-*                  → UniversalAgent (Google)
      grok-*                   → UniversalAgent (xAI)
      qwen-*                   → UniversalAgent (Alibaba)
      <anything else>           → OllmaAgent (local Ollama)
    """
    from faultseeker.utils.agent import build_provider_agent

    if router:
        return RoutedAgent(system_prompt, router, agent_role, provider_factory or build_provider_agent)
    selected_model = model_name

    # Guard: never pass an empty model string
    if not selected_model or not selected_model.strip():
        selected_model = router.local_model if router else 'phi3:mini'

    agent = build_provider_agent(system_prompt, selected_model)
    return agent
