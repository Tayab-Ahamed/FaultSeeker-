# Cohort v3 local TRAIN commands

The original14-row publication remains immutable. The expanded version has20 authenticated rows:14TRAIN and6heldout, grouped by incident while preserving all original memberships. No heldout command should run before the final frozen system is ready for its exactly-once exam.

```powershell
python scripts/run_authentic_research.py --split-file benchmark/versions/cohort_v3_20261016/eval_split.json
python scripts/run_train_production.py --split-file benchmark/versions/cohort_v3_20261016/eval_split.json
```

Both commands use only cached real TRAIN inputs and record missing coverage explicitly. They perform no network/provider dispatch. A missing capture is not a negative prediction. Neither command establishes complete multi-agent localization, overall system F1, billed cost savings, or the paper metrics. New TRAIN rows still require actual capture acquisition before complete coverage is possible.

Publication reproduction, with a new output directory to preserve existing artifacts:

```powershell
python scripts/extend_authentic_cohort.py --parent-split benchmark/eval_split.json --additions-manifest reports/cohort_rebuild_v2/additional_admitted_manifests/20261016T063056.json --output-directory build/cohort_v3_reproduction --incident-aliases reports/cohort_rebuild_v3/incident_aliases.json --seed 1729
```

Use `--seed 1729` (separate option and value). The publisher refuses overwriting an existing directory. Membership is reproducible; output-path-dependent artifact hashes differ when the output directory changes.
