"""
FaultSeeker++ — Result Visualization (Task A)
Generates charts from the 246-entry benchmark dataset.
Outputs PNG files to reports/charts/
"""
import csv
import json
import os
from collections import Counter
from pathlib import Path

# Use only stdlib + matplotlib (already in venv)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

CSV_PATH = Path("benchmark/benchmark_classification_fixed.csv")
OUT_DIR  = Path("reports/charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────
chains, vulns, complexities, losses = [], [], [], []

with open(CSV_PATH, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if not row.get("txn_hash","").strip():
            continue
        chains.append(row.get("chain","").strip().lower())
        vulns.append(row.get("vuln_type","").strip())
        complexities.append(row.get("class","").strip())
        try:
            losses.append(float(row.get("loss_usd","0").replace(",","")))
        except:
            losses.append(0.0)

N = len(chains)
print(f"Loaded {N} entries")

# ── Palette ────────────────────────────────────────────────────────────
CHAIN_COLORS = {
    "eth":       "#627EEA",
    "bsc":       "#F3BA2F",
    "arbitrum":  "#28A0F0",
    "optimism":  "#FF0420",
    "base":      "#0052FF",
    "polygon":   "#8247E5",
    "avalanche": "#E84142",
    "zksync":    "#1E69FF",
}
COMPLEXITY_COLORS = {
    "Simple":                "#4CAF50",
    "Moderate":              "#2196F3",
    "Complex":               "#FF9800",
    "Exceptionally Complex": "#F44336",
}

plt.rcParams.update({
    "font.family":    "DejaVu Sans",
    "font.size":      11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#1a1d27",
    "axes.edgecolor":   "#3d4166",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#c9d1d9",
    "ytick.color":      "#c9d1d9",
    "text.color":       "#c9d1d9",
    "grid.color":       "#2d3153",
    "grid.linewidth":   0.6,
})

# ══════════════════════════════════════════════════════════════════════
# Chart 1 — Chain Distribution (Horizontal Bar)
# ══════════════════════════════════════════════════════════════════════
chain_counts = Counter(chains)
chain_labels = [c.upper() for c in CHAIN_COLORS if c in chain_counts]
chain_values = [chain_counts[c] for c in CHAIN_COLORS if c in chain_counts]
chain_cols   = [CHAIN_COLORS[c] for c in CHAIN_COLORS if c in chain_counts]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(chain_labels, chain_values, color=chain_cols, height=0.6, edgecolor="none")
for bar, val in zip(bars, chain_values):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
            f"  {val}  ({val/N*100:.1f}%)", va="center", fontsize=10)
ax.set_xlabel("Number of Transactions")
ax.set_title("FaultSeeker++ Dataset — Chain Distribution (246 Transactions)")
ax.set_xlim(0, max(chain_values) * 1.25)
ax.grid(axis="x", alpha=0.5)
plt.tight_layout()
p1 = OUT_DIR / "chart1_chain_distribution.png"
plt.savefig(p1, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {p1}")

# ══════════════════════════════════════════════════════════════════════
# Chart 2 — Top 12 Vulnerability Types (Horizontal Bar)
# ══════════════════════════════════════════════════════════════════════
vuln_counts = Counter(vulns).most_common(12)
v_labels = [v[0] for v in vuln_counts]
v_values = [v[1] for v in vuln_counts]
grad_cols = plt.cm.plasma(np.linspace(0.2, 0.85, len(v_labels)))

fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.barh(v_labels[::-1], v_values[::-1], color=grad_cols[::-1], height=0.6, edgecolor="none")
for bar, val in zip(bars, v_values[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"  {val}", va="center", fontsize=10)
ax.set_xlabel("Count")
ax.set_title("Top 12 Vulnerability Types — FaultSeeker++ Benchmark")
ax.set_xlim(0, max(v_values) * 1.2)
ax.grid(axis="x", alpha=0.5)
plt.tight_layout()
p2 = OUT_DIR / "chart2_vuln_types.png"
plt.savefig(p2, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {p2}")

# ══════════════════════════════════════════════════════════════════════
# Chart 3 — Complexity Distribution (Donut)
# ══════════════════════════════════════════════════════════════════════
comp_order  = ["Simple","Moderate","Complex","Exceptionally Complex"]
comp_counts = [sum(1 for c in complexities if c==l) for l in comp_order]
comp_colors = [COMPLEXITY_COLORS[l] for l in comp_order]

fig, ax = plt.subplots(figsize=(8, 6))
wedges, texts, autotexts = ax.pie(
    comp_counts, labels=None,
    colors=comp_colors, autopct="%1.1f%%",
    startangle=140, pctdistance=0.75,
    wedgeprops=dict(width=0.52, edgecolor="#0f1117", linewidth=2),
)
for at in autotexts:
    at.set_fontsize(12)
    at.set_color("white")
    at.set_fontweight("bold")
legend_items = [
    mpatches.Patch(color=COMPLEXITY_COLORS[l], label=f"{l} ({c})")
    for l, c in zip(comp_order, comp_counts)
]
ax.legend(handles=legend_items, loc="lower center",
          bbox_to_anchor=(0.5, -0.12), ncol=2, framealpha=0.2)
ax.set_title("Transaction Complexity Distribution")
plt.tight_layout()
p3 = OUT_DIR / "chart3_complexity_donut.png"
plt.savefig(p3, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {p3}")

# ══════════════════════════════════════════════════════════════════════
# Chart 4 — Vulnerability Types Per Chain (Stacked Bar)
# ══════════════════════════════════════════════════════════════════════
top_vulns_list = [v[0] for v in Counter(vulns).most_common(6)]
chain_order = [c for c in CHAIN_COLORS if c in chain_counts]

data_matrix = []
for vt in top_vulns_list:
    row_data = []
    for ch in chain_order:
        count = sum(1 for c,v in zip(chains,vulns) if c==ch and v==vt)
        row_data.append(count)
    data_matrix.append(row_data)

fig, ax = plt.subplots(figsize=(12, 6))
bottoms = [0]*len(chain_order)
bar_colors = plt.cm.tab10(np.linspace(0, 0.9, len(top_vulns_list)))
x = np.arange(len(chain_order))
for i, (vt, row_data) in enumerate(zip(top_vulns_list, data_matrix)):
    bars = ax.bar(x, row_data, bottom=bottoms, color=bar_colors[i],
                  label=vt, edgecolor="#0f1117", linewidth=0.5)
    bottoms = [b+r for b,r in zip(bottoms, row_data)]

ax.set_xticks(x)
ax.set_xticklabels([c.upper() for c in chain_order])
ax.set_ylabel("Transaction Count")
ax.set_title("Top Vulnerability Types per Chain")
ax.legend(loc="upper right", fontsize=9, framealpha=0.3)
ax.grid(axis="y", alpha=0.4)
plt.tight_layout()
p4 = OUT_DIR / "chart4_vuln_per_chain.png"
plt.savefig(p4, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {p4}")

# ══════════════════════════════════════════════════════════════════════
# Chart 5 — Loss USD Distribution (Log scale histogram)
# ══════════════════════════════════════════════════════════════════════
nonzero_losses = [l for l in losses if l > 0]
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(nonzero_losses, bins=40, color="#627EEA", edgecolor="#0f1117",
        linewidth=0.5, log=True, alpha=0.9)
ax.set_xscale("log")
ax.set_xlabel("Loss (USD) — Log Scale")
ax.set_ylabel("Number of Transactions (Log)")
ax.set_title("Distribution of Financial Losses Across Exploits")
ax.grid(axis="both", alpha=0.4)
# Add percentile lines
for pct, label, col in [(50,"Median","#F3BA2F"),(90,"P90","#F44336")]:
    val = np.percentile(nonzero_losses, pct)
    ax.axvline(val, color=col, linestyle="--", linewidth=1.5, label=f"{label}: ${val:,.0f}")
ax.legend(framealpha=0.3)
plt.tight_layout()
p5 = OUT_DIR / "chart5_loss_distribution.png"
plt.savefig(p5, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {p5}")

# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════
print(f"\n✅ All 5 charts saved to: {OUT_DIR.resolve()}")
print(f"   chart1_chain_distribution.png")
print(f"   chart2_vuln_types.png")
print(f"   chart3_complexity_donut.png")
print(f"   chart4_vuln_per_chain.png")
print(f"   chart5_loss_distribution.png")
