from common import ROOT, describe, read_json, run


def compute():
    """Recalculate localization accuracy from recorded hits and denominator only."""
    path = ROOT / "reports/honest_results/localization_metrics.json"
    metrics = read_json(path)["metrics"]
    hits, total = metrics["top_1_hits"], metrics["evaluated"]
    if not 0 <= hits <= total or total <= 0:
        raise ValueError("Invalid localization counts")
    describe(path, 1, f"aggregate; represented evaluation rows={total}")
    print(f"Stored top-1 hits={hits}/{total}. Raw ranked predictions unavailable; this reproduces aggregate arithmetic, not localization execution.")
    return {"localization_top1_pct": 100 * hits / total}


if __name__ == "__main__":
    raise SystemExit(run(compute))
