"""Opt-in routing/cost audit that separates observed usage from estimates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class RouteObservation:
    tier: int
    model: str
    local: bool
    input_tokens: int
    output_tokens: int
    usage_source: str
    cost_usd: float
    status: str = "success"


class RoutingAudit:
    """Record decisions without making calls or assuming a provider response."""

    def __init__(self, pricing: Mapping[str, Mapping[str, float]], local_models: set[str] | frozenset[str] = frozenset()):
        self.pricing = {str(k): dict(v) for k, v in pricing.items()}
        self.local_models = frozenset(local_models)
        self.observations: list[RouteObservation] = []

    def record(
        self,
        *,
        tier: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        usage_source: str = "provider",
        cost_usd: float | None = None,
        status: str = "success",
    ) -> RouteObservation:
        if tier not in (1, 2, 3):
            raise ValueError("tier must be 1, 2, or 3")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (input_tokens, output_tokens)):
            raise ValueError("token counts must be nonnegative integers")
        if usage_source not in {"provider", "estimate", "reservation", "not-dispatched"}:
            raise ValueError("unsupported usage source")
        local = model in self.local_models
        if not local and model not in self.pricing:
            raise ValueError(f"unknown model pricing for {model}; declare it in local_models or pricing")
        if cost_usd is None:
            if local:
                cost_usd = 0.0
            else:
                rates = self.pricing[model]
                cost_usd = (input_tokens * rates.get("input", rates.get("prompt", 0.0)) +
                            output_tokens * rates.get("output", rates.get("completion", 0.0))) / 1_000_000
        if not math.isfinite(float(cost_usd)) or cost_usd < 0:
            raise ValueError("cost must be nonnegative")
        observation = RouteObservation(tier, model, local, input_tokens, output_tokens, usage_source, float(cost_usd), status)
        self.observations.append(observation)
        return observation

    def summary(self, cloud_model: str) -> dict[str, Any]:
        if cloud_model not in self.pricing:
            raise ValueError(f"unknown cloud pricing for {cloud_model}")
        rates = self.pricing[cloud_model]
        actual = sum(item.cost_usd for item in self.observations)
        cloud_only = sum((item.input_tokens * rates.get("input", rates.get("prompt", 0.0)) +
                          item.output_tokens * rates.get("output", rates.get("completion", 0.0))) / 1_000_000
                         for item in self.observations)
        observed = sum(item.usage_source == "provider" for item in self.observations)
        estimated = len(self.observations) - observed
        return {
            "queries": len(self.observations),
            "local_queries": sum(item.local for item in self.observations),
            "cloud_queries": sum(not item.local for item in self.observations),
            "observed_usage_queries": observed,
            "estimated_usage_queries": estimated,
            "actual_or_recorded_cost_usd": round(actual, 10),
            "counterfactual_cloud_cost_usd": round(cloud_only, 10),
            "cost_reduction_is_observed": estimated == 0,
            "records": [asdict(item) for item in self.observations],
        }
