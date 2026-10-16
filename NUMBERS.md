# Headline number definitions

These definitions keep the demo's numbers reproducible and scoped.

| Number | What it measures | What it is not | Status |
|---|---|---|---|
| F1 **0.7586** | `2*154/(2*154+21+77)` from the saved full-system confusion counts in `reports/honest_results/baseline_comparison.csv` over 1,231 historical/control rows. | Not a fresh live run, not the paper's separate SSTORE detector F1, and not proof that the legacy labels are independently adjudicated. | Measured as a saved feature-harness aggregate; reproduced offline. |
| Cost saving **35%** | Modeled reduction from $0.060 to $0.039 per query using the stored 50/30/20 tier assumptions. | Not observed billing, not a provider invoice, and not the older mislabeled 58% Tier-2-only figure. | Modeled. |
| Top-1 localization **6.1% (7/115)** | Seven recorded top-1 function hits divided by 115 recorded evaluations in `reports/honest_results/localization_metrics.json`. | Not a rerun of raw rankings; the original ranked prediction files are not present. | Saved aggregate reproduced offline. |
| Reentrancy labels **17** | Count of 231 frozen CSV `vuln_type` strings containing `reentran`, case-insensitively. | Not 17 independently verified incidents and not the paper's unsupported 18-row evaluation claim. | Measured string count. |
| Vulnerability labels **82** | Count of distinct non-empty exact `vuln_type` strings in the frozen 231-row CSV. | Not 82 semantic or independently adjudicated vulnerability classes. | Measured string count. |
| Cohort size **231** | Number of rows in the exact frozen snapshot used by the offline reproduction scripts. | Not the current accepted manifest size, not the historical 246-row CSV, and not the 1,059-row candidate pool. | Measured row count. |
| Chains **8** | Number of distinct chain strings in that same frozen 231-row CSV. | Not proof of the paper's claimed ten-chain cohort or current accepted-cohort coverage. | Measured distinct-value count. |

The exact commands and inputs are in `REPRODUCING.md`.
