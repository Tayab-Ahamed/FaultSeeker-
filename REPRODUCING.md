# Reproducing the audited headline numbers

These commands are offline and use only files already in this repository. They
do not replay transactions, call RPC providers, call models, or read the
held-out split.

Run from the repository root:

```bash
.venv/bin/python scripts/reproduce/honest_f1.py
.venv/bin/python scripts/reproduce/modeled_cost.py
.venv/bin/python scripts/reproduce/localization.py
.venv/bin/python scripts/reproduce/reentrancy_count.py
.venv/bin/python scripts/reproduce/vulnerability_count.py
.venv/bin/python scripts/reproduce/cohort.py
```

Clean-clone prerequisite: `.venv/` is intentionally not committed. The six
direct helper scripts above and `reports/reproducibility/FINAL_REPORT.md` must
also be present in the checkout used for this historical reproduction. A
clean Git clone of `demo-ready` currently contains `run_all.py` and
`claim_evidence.py`, but not those earlier working-tree helper files or the
local virtual environment; the commands consequently fail with exit 127 until
the environment and those files are provisioned. This is a packaging blocker,
not a hidden runtime step, and no live or paid dependency is implied.

Run the complete check and summary table with:

```bash
.venv/bin/python scripts/reproduce/run_all.py
```

The runner executes every direct reproduction script except `common.py` and
itself. It compares the reproduced values with the expected values in
`reports/reproducibility/FINAL_REPORT.md`.

Build the offline claim-audit artifacts with:

```bash
.venv/bin/python scripts/reproduce/claim_evidence.py
```

This writes `reports/claim_evidence/`, including:

- `CLAIMS_STATUS.md` — the 18-row `VERIFIED` / `REWORD` / `DROP` review;
- `summary.json` — cohort counts, label counts, and saved localization values;
- `chain_shares.csv` and `class_proportions.csv`;
- `vulnerability_swc_mapping.csv` — all distinct label strings and the SWC
  classification already present in the frozen CSV, without inventing mappings;
- `cohort_provenance_gaps.csv` and `reentrancy_rows.csv`;
- `chain_capability_matrix.csv` — free-endpoint observations and their limits;
- `table_v_saved_results.csv` and `localization_summary.json`.

The claim-audit command is also offline: it reads only the frozen cohort and
saved result artifacts. It does not replay transactions, call RPC providers,
call models, or access paid services.

## Exact inputs

| Number | Input |
|---|---|
| F1 | `reports/honest_results/baseline_comparison.csv` |
| Modeled cost saving | `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json` |
| Top-1 localization | `reports/honest_results/localization_metrics.json` |
| Reentrancy label count | `reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8/benchmark/benchmark_classification_fixed.csv` |
| Vulnerability label count | `reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8/benchmark/benchmark_classification_fixed.csv` |
| Cohort rows and chain count | `reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8/benchmark/benchmark_classification_fixed.csv` |

The scripts print the input path, row count where applicable, SHA-256 digest,
expected value, reproduced value, and pass/fail status. The values are scoped
historical reproductions; they do not authenticate the paper's empirical study.
