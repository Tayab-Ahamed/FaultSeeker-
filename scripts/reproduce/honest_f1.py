from common import ROOT, read_csv, run


def compute():
    """Recalculate historical F1 from saved confusion counts, not a new evaluation."""
    rows = read_csv(ROOT / "reports/honest_results/baseline_comparison.csv")
    selected = [r for r in rows if r["system"] == "FaultSeeker++ (Ours)"]
    if len(selected) != 1:
        raise ValueError("Expected exactly one full-system aggregate")
    row = selected[0]
    tp, fp, tn, fn = (int(row[k]) for k in ("tp", "fp", "tn", "fn"))
    if min(tp, fp, tn, fn) < 0 or tp + fp + tn + fn != int(row["n"]):
        raise ValueError("Inconsistent confusion counts")
    print(f"Used aggregate rows=1; represented cases={row['n']}; TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print("Scope: stored feature-harness result; includes the historically flagged 1000 benign-feature controls. Not independent research validation or a live model run.")
    return {"honest_f1": 2 * tp / (2 * tp + fp + fn)}


if __name__ == "__main__":
    raise SystemExit(run(compute))
