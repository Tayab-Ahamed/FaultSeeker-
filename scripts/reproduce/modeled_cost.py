from common import COST, describe, read_json, run


def compute():
    """Recalculate modeled savings from the corrected historical pricing assumptions."""
    inputs = read_json(COST)["inputs"]
    fractions = inputs["tier_fractions"]
    if abs(sum(fractions.values()) - 1) > 1e-9 or min(fractions.values()) < 0:
        raise ValueError("Invalid tier fractions")
    hybrid = fractions["tier2"] * inputs["tier2_hybrid_cost_per_query_usd"] + fractions["tier3"] * inputs["tier3_cost_per_query_usd"]
    cloud = fractions["tier2"] * inputs["tier2_cloud_cost_per_query_usd"] + fractions["tier3"] * inputs["tier3_cost_per_query_usd"]
    describe(COST, 3, "tier assumptions; observed transaction rows=0")
    print(f"Modeled USD/query: hybrid={hybrid}; cloud={cloud}. Tier1 costs zero in BOTH modes. Not measured billing or savings.")
    return {"modeled_cost_saving_pct": 100 * (cloud - hybrid) / cloud}


if __name__ == "__main__":
    raise SystemExit(run(compute))
