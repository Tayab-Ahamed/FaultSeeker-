# Reproducing the audited headline numbers

These commands are offline and use only files already in this repository. They
do not replay transactions, call RPC providers, call models, or read the
held-out split.

On Windows, keep `core.autocrlf=false` when cloning because several
digest-bound JSON inputs must retain LF bytes exactly.

Run from the repository root:

```bash
.venv/bin/python scripts/reproduce/honest_f1.py
.venv/bin/python scripts/reproduce/modeled_cost.py
.venv/bin/python scripts/reproduce/localization.py
.venv/bin/python scripts/reproduce/reentrancy_count.py
.venv/bin/python scripts/reproduce/vulnerability_count.py
.venv/bin/python scripts/reproduce/cohort.py
```

On Windows Git Bash, replace `.venv/bin/python` with
`.venv/Scripts/python.exe`. In PowerShell, use `.venv\Scripts\python.exe`.

Clean-clone prerequisite: the six direct helper scripts above,
`scripts/reproduce/common.py`, and `reports/reproducibility/FINAL_REPORT.md`
are tracked in this branch. `.venv/` is intentionally not committed, so a
clean Git clone still requires the project environment to be provisioned
before these exact commands can run. This is an environment prerequisite, not
a hidden runtime step, and no live or paid dependency is implied.

Run the complete check and summary table with:

```bash
.venv/bin/python scripts/reproduce/run_all.py
```

Run the independent upstream comparison (offline, using the retained
115-row upstream labels and provider-pinned LLM-free outputs) with:

```bash
.venv/bin/python scripts/reproduce/independent_upstream_validation.py
```

This writes `reports/reproducibility/upstream_validation/` containing the
machine-readable 31-claim comparison, a readable report, an input SHA-256
manifest, and one retained per-example localization record. Failed rows remain
in the 115-row denominator, and the output is explicitly marked an independent
calculation rather than an exact paper reproduction. It performs no RPC,
provider, LLM, or upstream rerun.

The source manuscript is `paper/blockchain_exploit_forensics_survey_ieee.tex`.
The repository has no LaTeX compiler in the current environment, so source
structure and citation-key checks can be run locally, but PDF compilation is
unverified:

```bash
python -c "from pathlib import Path; p=Path('paper/blockchain_exploit_forensics_survey_ieee.tex').read_text(encoding='utf-8'); assert p.count(r'\\begin{document}') == p.count(r'\\end{document}') == 1; assert p.count(r'\\begin{table}') == p.count(r'\\end{table}'); assert r'\\bibitem{faultseeker_upstream}' in p"
```

Frozen-evidence checks are read-only:

```bash
python scripts/research/verify_batch_e_result.py
python -m benchmark.validate_cohort_manifest benchmark/cohort_manifest.json --root .
python -m benchmark.validate_cohort_manifest benchmark/versions/cohort_v4_20261016/cohort_manifest.json --root .
```

Do not rerun scoring against frozen Batch D or Batch E. Their freeze hashes and
one-pass outputs are recorded in
`reports/reproducibility/UPSTREAM_VALIDATION_CLOSEOUT_20261019.md`.

The runner executes every direct metric reproduction script except `common.py`,
`claim_evidence.py`, and itself. It compares the reproduced values with the expected values in
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
