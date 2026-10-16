# Offline reproduction of reported historical numbers

This report defines the expected values requested for reproduction. It does not
replace the earlier claim decisions or verify the paper's empirical claims.
Each command recalculates from existing files without network calls, model code,
current cohort mutation, or held-out evaluation. Only Python's standard library
is required. Run from the repository root; scripts also work from another cwd.

| Metric | Expected | Decimal places | Meaning |
|---|---|---|---|
| honest_f1 | 0.7586 | 4 | Saved full-system confusion counts: TP154 FP21 TN979 FN77 |
| modeled_cost_saving_pct | 35.0 | 1 | Corrected tier mixture, assumed costs; not measured savings |
| localization_top1_pct | 6.1 | 1 | Recorded 7 hits / 115 evaluations; not a rerun of rankings |
| reentrancy_label_count | 17 | 0 | Case-insensitive reentran substring in frozen vuln_type |
| vulnerability_label_count | 82 | 0 | Distinct nonempty exact vuln_type strings, not semantic types |
| cohort_rows | 231 | 0 | Frozen fca6b99 CSV rows, not provenance-accepted incidents |
| chain_count | 8 | 0 | Distinct chain strings in that frozen CSV |

Commands (one per headline number):

```powershell
python scripts/reproduce/honest_f1.py
python scripts/reproduce/modeled_cost.py
python scripts/reproduce/localization.py
python scripts/reproduce/reentrancy_count.py
python scripts/reproduce/vulnerability_count.py
python scripts/reproduce/cohort.py
```

Every command prints absolute input paths, SHA-256 digests, input row counts,
represented population where applicable, and expected/reproduced values. Values
are compared after decimal rounding HALF_UP to the precision shown above;
any mismatch, missing input, or missing expected metric exits nonzero.
`--report PATH` explicitly selects another expected-value report for auditing.
No expected metric is taken from a model constant or from the saved metric field
itself: F1 uses confusion counts, localization uses hit counts, cost uses inputs.

Inputs and important limits:

- `reports/honest_results/baseline_comparison.csv`: saved feature-harness
  aggregates. The full-system row represents 1231 cases (231 historical exploits
  plus the previously flagged 1000 benign-feature controls). This script only
  recalculates stored counts. Those controls are not a valid independent benign
  population, and this result is not newly accepted research evidence.
- `reports/honest_results/localization_metrics.json`: one saved aggregate,
  seven top-1 hits / 115 evaluations. Original raw ranked predictions are missing;
  recalculation cannot establish that the original localization execution was valid.
- `reports/canonical_history/snapshots/b96f53ce1d6634a1e1cc11659eb37ab15fcf29a6/reports/research_results/runtime_cost.json`:
  corrected October cost assumptions. Hybrid .3*.05+.2*.12=.039 versus cloud
  .3*.12+.2*.12=.060 USD/query, giving 35%. Tier1 is free in both modes.
  There are three assumed tier rows and zero measured transaction observations.
- `reports/canonical_history/snapshots/fca6b998fa0a01f3832be6a0f1aa1d768306da8f/benchmark/benchmark_classification_fixed.csv`:
  the 231-row labeled historical version, deliberately distinct from the newer
  provenance-admitted cohort. Counting its labels does not establish their truth.

`cohort_provenance.csv` copies source URLs only from each historical row's
`analysis` field; absent URLs are `no source`. `label_source` identifies the
actual frozen CSV and `vuln_type` column, not an independent adjudicator. Links
are not fetched, authenticated, or inferred from an incident name. One legacy
`analysis` cell has malformed list quoting; its explicitly written URL is
extracted without guessing or repairing the link. Regenerate:

```powershell
python scripts/reproduce/cohort.py --write-provenance
```

No synthetic rows or results are created by these scripts. Existing historical
aggregates are identified as such, including their limitations. No held-out data
is read by the reproduction commands. Unit tests remain software checks only.
